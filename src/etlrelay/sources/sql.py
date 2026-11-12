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
    """Read SQL query results into an Arrow-backed batch.

    The source executes a SQL query using a caller-provided SQLAlchemy engine
    and converts the results into a single :class:`Batch`. All result rows
    are materialized in memory before the batch is constructed.

    An empty result set produces no batches. The source does not own or
    dispose of the engine supplied by the caller.
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
            query: SQL query to execute. Named bind parameters can be
                specified using SQLAlchemy's ``:name`` syntax.
            parameters: Optional mapping of named bind parameters to their
                values. Values are bound separately from the SQL statement.
            batch_size: Optional batch size for the resulting batches.
        """
        self._validate_batch_size(batch_size)

        self._engine = engine
        self._query = query
        self._parameters = parameters
        self._batch_size = batch_size
        self._execution_mode = self._fetch_batch if batch_size is None else self._yield_batch

    def read(self) -> Iterator[Batch]:
        """Execute the query and return its results as batches.

        Returns:
            An iterable containing one batch if the query returns rows,
            or an empty iterable if the result set is empty.

        Raises:
            ValueError: If the query returns duplicate column names.
            SQLAlchemyError: If query execution fails.

        Note:
            The query result and connection are closed after row retrieval,
            including when retrieval fails. Arrow conversion occurs after
            the connection is released and may raise Arrow conversion errors.
            All rows are materialized in memory; this is not a streaming query.
            The supplied engine remains owned by the caller and is not disposed.
        """
        return self._execution_mode()

    def _fetch_batch(self) -> Iterator[Batch]:
        with self._execute_query() as result:
            rows = [dict(row) for row in result.mappings()]
            if not rows:
                logger.debug("SQL source read completed (0 rows).")
                return iter([])

            batch = self._rows_to_batch(rows)
            logger.debug("SQL source read completed (%d rows).", len(rows))
            return iter([batch])

    def _yield_batch(self) -> Iterator[Batch]:
        with self._execute_query(streaming=True) as result:
            partitions = result.mappings().partitions(self._batch_size)

            for partition in partitions:
                rows = [dict(row) for row in partition]
                batch = self._rows_to_batch(rows)
                yield batch

    @contextmanager
    def _execute_query(self, streaming: bool = False) -> Generator[CursorResult, None, None]:
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
            A batch containing a PyArrow table inferred from the row values.
            Null values are preserved according to PyArrow's type inference.
        """
        return Batch(table=pa.Table.from_pylist(list(rows)))

    @staticmethod
    def _validate_batch_size(batch_size: int | None) -> None:
        """Validate the batch size parameter.

        Args:
            batch_size: The batch size to validate.

        Raises:
            ValueError: If the batch size is not a positive integer.
        """
        if batch_size is None or (
            isinstance(batch_size, int) and batch_size > 0 and not isinstance(batch_size, bool)
        ):
            return
        raise ValueError("Batch size must be a positive integer.")
