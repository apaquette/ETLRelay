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

    An empty result set produces no batches. Result ordering follows the order
    returned by the database; use an SQL ``ORDER BY`` clause when deterministic
    ordering is required.

    The source manages the connections and query results it acquires but does
    not own or dispose of the supplied engine.
    """

    def __init__(
        self,
        engine: Engine,
        query: str,
        *,
        parameters: Mapping[str, Any] | None = None,
        batch_size: int | None = None,
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
                results are consumed incrementally in batches of this size.

        Raises:
            ValueError: If ``batch_size`` is not ``None`` or a positive integer.
                Boolean values are not accepted as integers.
        """
        self._validate_batch_size(batch_size)

        self._engine = engine
        self._query = query
        self._parameters = parameters
        self._batch_size = batch_size
        self._execution_mode = self._fetch_batch if batch_size is None else self._yield_batch

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
            ValueError: If the query returns duplicate column names.
            SQLAlchemyError: If establishing the connection or executing the
                query fails.
            Exception: Other exceptions raised during result retrieval or Arrow
                conversion propagate to the caller.

        Note:
            In the default execution mode, the query result and connection are
            closed before this method returns. In batched mode, they remain open
            while the generator is being consumed and are closed when iteration
            completes, an exception occurs, or the generator is closed.

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

            batch = self._rows_to_batch(rows)
            logger.debug("SQL source read completed (%d rows).", len(rows))
            return iter([batch])

    def _yield_batch(self) -> Iterator[Batch]:
        """Incrementally consume the query result and yield Arrow-backed batches.

        The query is executed using SQLAlchemy's streaming execution option.
        Result rows are consumed in partitions no larger than the configured
        batch size, with each partition converted into a separate batch.

        An empty result produces no batches. The final batch may contain fewer
        rows than the configured batch size.

        Yields:
            Arrow-backed batches containing no more than the configured number
            of rows.

        Note:
            The query result and connection remain open while the generator is
            being consumed. They are released when iteration completes, an
            exception occurs, or the generator is closed.
        """
        with self._execute_query(streaming=True) as result:
            partitions = result.mappings().partitions(self._batch_size)

            for partition in partitions:
                rows = [dict(row) for row in partition]
                batch = self._rows_to_batch(rows)
                yield batch

    @contextmanager
    def _execute_query(self, streaming: bool = False) -> Generator[CursorResult, None, None]:
        """Execute the configured SQL query within a managed connection context.

        A connection is acquired from the caller-provided engine and used to
        execute the configured query and parameters. Result column names are
        validated before the result is made available.

        When streaming is enabled, SQLAlchemy's ``yield_per`` execution option
        is configured using the source's batch size before query execution.

        Args:
            streaming: Whether to configure SQLAlchemy's streaming execution
                option for the query.

        Yields:
            The SQLAlchemy cursor result containing the query results.

        Raises:
            ValueError: If the query returns duplicate column names.
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
                self._validate_column_names(list(result.keys()))
                yield result
            finally:
                result.close()

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
    def _rows_to_batch(rows: list[dict[str, Any]]) -> Batch:
        """Convert materialized SQL rows into an Arrow-backed batch.

        Args:
            rows: Non-empty list of database rows represented as dictionaries.

        Returns:
            A batch containing a PyArrow table constructed from the supplied rows.
            PyArrow infers column types from the row values.
        """
        return Batch(table=pa.Table.from_pylist(rows))

    @staticmethod
    def _validate_batch_size(batch_size: int | None) -> None:
        """Validate the optional batch size.

        Args:
            batch_size: Maximum number of rows per batch. ``None`` disables
                batching and preserves the default single-batch behaviour.

        Raises:
            ValueError: If ``batch_size`` is not ``None`` or a positive integer.
                Boolean values are explicitly rejected.
        """
        if batch_size is None or (
            isinstance(batch_size, int) and batch_size > 0 and not isinstance(batch_size, bool)
        ):
            return
        raise ValueError("Batch size must be a positive integer.")
