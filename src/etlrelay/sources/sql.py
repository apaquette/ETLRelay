"""SQL-backed data source."""

import logging
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pyarrow as pa
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

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
    ) -> None:
        """Initialize the SQL source.

        Args:
            engine: SQLAlchemy engine used to establish database connections.
                The caller retains responsibility for its lifecycle.
            query: SQL query to execute. Named bind parameters can be
                specified using SQLAlchemy's ``:name`` syntax.
            parameters: Optional mapping of named bind parameters to their
                values. Values are bound separately from the SQL statement.
        """
        self._engine = engine
        self._query = query
        self._parameters = parameters

    def read(self) -> Iterable[Batch]:
        """Execute the query and return its results as batches.

        Returns:
            An iterable containing one batch if the query returns rows,
            or an empty iterable if the result set is empty.

        Raises:
            ValueError: If the query returns duplicate column names.
            SQLAlchemyError: If query execution fails.
        """
        with self._engine.connect() as connection:
            rows = self._fetch_rows(connection)

        if not rows:
            logger.debug("SQL source read completed (0 rows).")
            return []

        batch = self._rows_to_batch(rows)

        logger.debug(
            "SQL source read completed (%d rows).",
            len(rows),
        )

        return [batch]

    def _fetch_rows(
        self,
        connection: Connection,
    ) -> list[dict[str, Any]]:
        """Execute the query and materialize its result rows.

        Args:
            connection: Active SQLAlchemy connection used to execute the query.

        Returns:
            A list of rows represented as dictionaries mapping column names
            to their corresponding values.

        Raises:
            ValueError: If the query returns duplicate column names.
            SQLAlchemyError: If query execution or result retrieval fails.

        Note:
            The result is closed after retrieval, including when an error
            occurs. The supplied connection remains under the caller's
            control.
        """
        result = connection.execute(
            text(self._query),
            self._parameters,
        )

        try:
            column_names = list(result.keys())
            self._validate_column_names(column_names)

            return [dict(row) for row in result.mappings()]
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
        return Batch(table=pa.Table.from_pylist(rows))
