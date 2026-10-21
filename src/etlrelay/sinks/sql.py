"""SQL-backed data sink."""

import logging
from collections import Counter
from collections.abc import Iterable, Sequence

from sqlalchemy import MetaData, Table
from sqlalchemy.engine import Connection, Engine

from etlrelay.core import Batch

logger = logging.getLogger(__name__)


class SqlSink:
    """Append Arrow-backed batches to an existing SQL table.

    The sink uses SQLAlchemy Core to construct and execute insert statements.
    Each non-empty batch is written in its own transaction, allowing successful
    batches to remain committed if a subsequent batch fails.

    The sink does not own or dispose of the supplied engine.
    """

    def __init__(
        self,
        engine: Engine,
        table_name: str,
        *,
        schema: str | None = None,
    ) -> None:
        """Initialize the SQL sink.

        Args:
            engine: SQLAlchemy engine used to connect to the target database.
                The caller retains responsibility for its lifecycle.
            table_name: Name of the existing database table to which batches
                will be appended.
            schema: Optional database schema containing the target table.
        """
        self._engine = engine
        self._table_name = table_name
        self._schema = schema

    def write(self, batches: Iterable[Batch]) -> None:
        """Append batches to the target SQL table.

        Each non-empty batch is inserted within its own transaction.
        Empty batches are skipped without opening a transaction. Batch columns
        are validated against the target table before insertion.

        Previously committed batches remain committed if a later batch fails.
        A failure during a batch write rolls back that batch's transaction
        and propagates the exception to the caller.

        Args:
            batches: Iterable of Arrow-backed batches containing rows to append.

        Raises:
            ValueError: If a batch contains duplicate column names or columns
                that do not exist in the target table.
            SQLAlchemyError: If table reflection or database execution fails,
                including missing tables and database constraint violations.

        Note:
            SqlSink borrows the supplied SQLAlchemy Engine and does not
            dispose it.

            Each nonempty batch is written in a separate transaction.
            A transaction commits only after its context manager exits
            successfully. Failed transactions are rolled back by SQLAlchemy,
            while previously committed batches remain committed.

            Zero-row batches are skipped before reflection, column validation,
            or transaction creation.

            Batch columns must be unique and exist in the destination table.
            Omitted destination columns are permitted when supported by
            database defaults, nullability, or other database rules.

            SqlSink does not create tables, migrate schemas, upsert rows,
            or provide a transaction spanning multiple batches.
        """
        target_table: Table | None = None

        for batch in batches:
            if batch.table.num_rows == 0:
                continue

            column_names = batch.table.column_names
            self._validate_unique_columns(column_names)
            rows = batch.table.to_pylist()

            with self._engine.begin() as connection:
                if target_table is None:
                    target_table = self._reflect_table(connection)

                self._validate_columns(column_names, target_table)
                connection.execute(target_table.insert(), rows)

            logger.debug(
                "SQL sink committed batch (%d rows).",
                len(rows),
            )

    def _reflect_table(self, connection: Connection) -> Table:
        """Reflect the target table's metadata using an active connection.

        Args:
            connection: Active SQLAlchemy connection used to inspect the
                target table's schema.

        Returns:
            A SQLAlchemy Table object representing the existing target table.
        """
        return Table(
            self._table_name,
            MetaData(),
            schema=self._schema,
            autoload_with=connection,
        )

    @staticmethod
    def _validate_unique_columns(column_names: Sequence[str]) -> None:
        """Reject batches containing duplicate column names.

        Args:
            column_names: Column names present in the batch.

        Raises:
            ValueError: If one or more column names appear more than once.
                The exception identifies the duplicated names.
        """
        duplicates = sorted(name for name, count in Counter(column_names).items() if count > 1)

        if duplicates:
            raise ValueError(f"Batch contains duplicate column names: {duplicates}")

    @staticmethod
    def _validate_columns(
        batch_columns: Sequence[str],
        target_table: Table,
    ) -> None:
        """Reject batch columns that are absent from the target table.

        Columns present in the target table may be omitted from a batch,
        allowing the database to supply defaults or handle nullable columns.

        Args:
            batch_columns: Column names present in the batch.
            target_table: Reflected SQLAlchemy table defining the accepted
                column names.

        Raises:
            ValueError: If the batch contains column names that do not exist
                in the target table.
        """
        unknown_columns = set(batch_columns) - set(target_table.c.keys())

        if unknown_columns:
            raise ValueError(
                f"Batch contains columns not present in target table: {sorted(unknown_columns)}"
            )
