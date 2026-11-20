"""SQL-backed data source."""

import logging
from collections import Counter
from collections.abc import Generator, Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

import pyarrow as pa
from sqlalchemy import CursorResult, text
from sqlalchemy.engine import Engine

from etlrelay.core import Batch

logger = logging.getLogger(__name__)


class SqlSource:
    """Read SQL query results into Arrow-backed batches.

    The source executes a SQL query using a caller-provided SQLAlchemy engine
    and converts the results into PyArrow-backed :class:`Batch` objects.

    By default, all query results are materialized and returned as a single
    batch. When ``batch_size`` is configured, results are consumed incrementally
    and yielded in batches containing no more than the configured number of rows.
    The final batch may contain fewer rows.

    An optional Arrow schema can be supplied to establish the canonical schema
    for the query, regardless of whether batching is enabled. Its field names
    and ordering must match the SQL result columns, and result values must be
    compatible with its field types and nullability.

    When no schema is supplied, the schema is inferred from the complete result
    in unbatched mode or from the first non-empty batch in batched mode.
    Subsequent batches retain the inferred schema and must contain compatible
    field names, ordering, data types, and nullability.

    Null-only columns in subsequent batches retain their established data types.
    However, a column initially inferred as the Arrow null type cannot be
    promoted to a concrete type by later batches. Supplying a schema allows
    callers to specify concrete types for columns containing only null values.

    An empty result set produces no batches. Supplied schema names and ordering
    are validated even when the result contains no rows. Result ordering follows
    the order returned by the database; use an SQL ``ORDER BY`` clause when
    deterministic ordering is required.

    The source manages the connections and query results it acquires but
    does not own or dispose of the supplied engine.
    """

    def __init__(
        self,
        engine: Engine,
        query: str,
        *,
        parameters: Mapping[str, Any] | None = None,
        batch_size: int | None = None,
        schema: pa.Schema | None = None,
    ) -> None:
        """Initialize the SQL source.

        Args:
            engine: SQLAlchemy engine used to establish database connections.
                The caller retains responsibility for its lifecycle.
            query: SQL query to execute. Named bind parameters can be specified
                using SQLAlchemy's ``:name`` syntax.
            parameters: Optional mapping of named bind parameters to their values.
                Values are bound separately from the SQL statement.
            batch_size: Optional maximum number of rows per batch. When ``None``,
                the complete result is returned as a single batch. When specified,
                results are consumed incrementally in batches of this size. Every
                batch produced by the query retains a consistent Arrow schema.
            schema: Optional canonical Arrow schema for the query. Its field
                names and ordering must match the SQL result columns. Result
                values must be compatible with the declared field types and
                nullability. When omitted, the schema is inferred from the
                query result.

        Raises:
            ValueError: If ``batch_size`` is not ``None`` or a positive integer.
                Boolean values are not accepted as integers.
        """
        self.validate_batch_size(batch_size)

        self._engine = engine
        self._query = query
        self._parameters = parameters
        self._batch_size = batch_size
        self._execution_mode = self._fetch_batch if batch_size is None else self._yield_batch
        self._schema = schema

    def read(self) -> Iterator[Batch]:
        """Execute the query and return its results as an iterator of batches.

        When batching is disabled, the query is executed immediately and all
        result rows are materialized into a single batch. An empty result produces
        an empty iterator.

        When batching is enabled, a generator is returned. Query execution and
        result consumption begin when the generator is first iterated. Each
        iteration produces the next batch, containing no more than the configured
        batch size. A final partial batch is produced when the remaining number
        of rows is smaller than the configured batch size.

        Returns:
            An iterator of Arrow-backed batches. The iterator contains either
            zero or one batch when batching is disabled, or zero or more batches
            when batching is enabled.

        Raises:
            ValueError: If the query returns duplicate column names, its result
                columns do not match the supplied schema, or result data has an
                incompatible schema.
            SQLAlchemyError: If establishing the connection or executing the
                query fails.
            Exception: Other exceptions raised during result retrieval or Arrow
                conversion propagate to the caller.

        Note:
            In the default execution mode, the query result and connection are
            closed before this method returns. In batched mode, they remain open
            while the generator is being consumed and are closed when iteration
            completes, an exception occurs, or the generator is closed.

            When a schema is supplied, it establishes the canonical schema
            regardless of execution mode. Otherwise, the schema is inferred
            from the complete result in unbatched mode or from the first
            non-empty batch in batched mode.

            Schema incompatibilities are raised when the incompatible result
            is processed. In streaming mode, this occurs during iteration.

            Consumers that stop iterating before exhaustion should explicitly
            close the generator to release SQL resources promptly.

            The supplied engine remains owned by the caller and is not disposed.
        """
        return self._execution_mode()

    def _fetch_batch(self) -> Iterator[Batch]:
        """Execute the query and materialize the complete result into one batch.

        The query result is fully consumed before the connection is released.
        If the result contains rows, they are converted into a single
        Arrow-backed batch. An empty result produces an empty iterator.

        Returns:
            An iterator containing one batch or no batches.

        Note:
            The complete query result is materialized in memory. The SQL result
            and connection are closed before the returned iterator is consumed.
        """
        with self._execute_query() as result:
            rows = [dict(row) for row in result.mappings()]
            if not rows:
                logger.debug("SQL source read completed (0 rows).")
                return iter([])
            batch, _ = self._create_batch(rows, self._schema)

            return iter([batch])

    def _yield_batch(self) -> Iterator[Batch]:
        """Incrementally consume the query result and yield Arrow-backed batches.

        The query is executed using SQLAlchemy's streaming execution option.
        Result rows are consumed in partitions no larger than the configured
        batch size, with each partition converted into a separate batch.

        The supplied schema, when present, establishes the canonical schema
        for the query execution. Otherwise, the schema inferred from the first
        non-empty batch establishes the canonical schema. Subsequent batches
        must have compatible field names, ordering, data types, and nullability.

        Null-only columns in subsequent batches retain their corresponding
        types from the canonical schema. Incompatible populated values cause
        a ValueError rather than automatic type promotion or conversion.

        An empty result produces no batches. The final batch may contain
        fewer rows than the configured batch size.

        Yields:
            Arrow-backed batches containing no more than the configured number
            of rows and sharing a consistent schema.

        Raises:
            ValueError: If the supplied or inferred canonical schema is
                incompatible with a batch.

        Note:
            The canonical schema is established independently for each
            execution. The query result and connection remain open while
            the generator is being consumed. They are released when iteration
            completes, an exception occurs, or the generator is closed.
        """
        canonical_schema: pa.Schema | None = self._schema
        with self._execute_query(streaming=True) as result:
            partitions = result.mappings().partitions(self._batch_size)

            for partition in partitions:
                rows = [dict(row) for row in partition]
                batch, schema = self._create_batch(rows, canonical_schema)
                canonical_schema = schema
                yield batch

    def _create_batch(
        self,
        rows: list[dict[str, Any]],
        expected_schema: pa.Schema | None = None,
    ) -> tuple[Batch, pa.Schema]:
        """Create an Arrow-backed batch using a canonical schema.

        The candidate Arrow table is constructed from the supplied rows.
        When an expected schema is provided, the candidate is validated
        against it and converted to that schema. Otherwise, its inferred
        schema becomes the canonical schema.

        Args:
            rows: Rows retrieved from the SQL query.
            expected_schema: Optional canonical schema established by the
                caller or an earlier batch.

        Returns:
            The constructed batch and the canonical schema used for it.

        Raises:
            ValueError: If the candidate table has incompatible field names,
                ordering, data types, or nullability.
        """
        candidate = pa.Table.from_pylist(rows)
        canonical_schema = expected_schema if expected_schema is not None else candidate.schema

        self._validate_batch_schema(candidate, canonical_schema)

        table = (
            candidate if expected_schema is None else candidate.cast(canonical_schema, safe=True)
        )

        logger.debug("SQL source created batch (%d rows).", len(rows))
        return Batch(table), canonical_schema

    @contextmanager
    def _execute_query(self, streaming: bool = False) -> Generator[CursorResult, None, None]:
        """Execute the configured SQL query within a managed connection context.

        A connection is acquired from the caller-provided engine and used to
        execute the configured query and parameters. Result column names are
        validated for uniqueness and, when an explicit schema is supplied,
        against its field names and ordering. This validation occurs even when
        the query returns no rows.

        When streaming is enabled, SQLAlchemy's ``yield_per`` execution option
        is configured using the source's batch size before query execution.

        Args:
            streaming: Whether to configure SQLAlchemy's streaming execution
                option for the query.

        Yields:
            The SQLAlchemy cursor result containing the query results.

        Raises:
            ValueError: If the query returns duplicate column names or its
                result columns do not match the supplied schema.
            SQLAlchemyError: If connection acquisition or query execution fails.

        Note:
            The result is closed when the context exits, including when result
            processing raises an exception. The connection is released by its
            context manager. The engine itself is not disposed.
        """
        with self._engine.connect() as connection:
            if streaming:
                connection.execution_options(yield_per=self._batch_size)
            result = connection.execute(
                text(self._query),
                self._parameters,
            )
            try:
                column_names = list(result.keys())
                self._validate_column_names(column_names)

                if self._schema is not None and column_names != self._schema.names:
                    raise ValueError(
                        "Incompatible names or ordering: "
                        f"expected {self._schema.names}, got {column_names}"
                    )

                yield result
            finally:
                result.close()

    @staticmethod
    def validate_batch_size(batch_size: int | None) -> None:
        """Validate the optional batch size.

        Args:
            batch_size: Maximum number of rows per batch. ``None`` disables
                batching and preserves the default single-batch behaviour.

        Raises:
            ValueError: If ``batch_size`` is neither ``None`` nor a positive
                integer. Boolean values are explicitly rejected.
        """
        if batch_size is None or (
            isinstance(batch_size, int) and batch_size > 0 and not isinstance(batch_size, bool)
        ):
            return
        raise ValueError("Batch size must be a positive integer.")

    @staticmethod
    def _validate_column_names(
        column_names: Sequence[str],
    ) -> None:
        """Ensure result column names are unique.

        Args:
            column_names: Column names returned by the SQL query.

        Raises:
            ValueError: If one or more column names occur more than once.
                The exception identifies the duplicated names.
        """
        duplicates = sorted(name for name, count in Counter(column_names).items() if count > 1)

        if duplicates:
            raise ValueError(f"SQL query returned duplicate column names: {duplicates}")

    @staticmethod
    def _validate_batch_schema(table: pa.Table, expected_schema: pa.Schema) -> None:
        """Validate a batch against its expected Arrow schema.

        Field names and ordering must match. Field data types must match,
        except that an inferred null type is compatible with an expected
        nullable field. Actual null values are rejected when the expected
        field is non-nullable.

        Schema and field metadata differences are ignored. This method
        validates compatibility without modifying or converting the table.

        Args:
            table: Arrow table representing the current batch.
            expected_schema: Canonical schema established for the query.

        Raises:
            ValueError: If field names, ordering, data types, or nullability
                are incompatible with the expected schema.
        """
        actual_schema = table.schema

        if actual_schema.names != expected_schema.names:
            raise ValueError(
                "Incompatible names or ordering: "
                f"expected {expected_schema.names}, got {actual_schema.names}"
            )

        for index, (actual_field, expected_field) in enumerate(
            zip(actual_schema, expected_schema, strict=True)
        ):
            null_count = table.column(index).null_count

            if not expected_field.nullable and null_count > 0:
                raise ValueError(
                    f"Schema field '{expected_field.name}' is non-nullable "
                    f"but contains {null_count} null values."
                )

            actual_type = actual_field.type
            expected_type = expected_field.type

            if actual_type.equals(expected_type) or pa.types.is_null(actual_type):
                continue

            raise ValueError(
                f"Incompatible type for schema field '{expected_field.name}': "
                f"expected {expected_type}, got {actual_type}"
            )
