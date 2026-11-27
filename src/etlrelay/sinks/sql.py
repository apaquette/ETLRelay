"""SQL-backed data sink."""

import logging
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import MetaData, Table
from sqlalchemy.engine import Connection, Engine

from etlrelay.core import Batch
from etlrelay.validation.sql import validate_engine as _validate_engine
from etlrelay.validation.sql import validate_unique_columns

logger = logging.getLogger(__name__)


class SqlSink:
    """Append Arrow-backed batches to an existing SQL table.

    The sink uses SQLAlchemy Core to construct and execute insert statements.
    Each non-empty batch is written in its own transaction, allowing successful
    batches to remain committed if a subsequent batch fails.

    The sink does not own or dispose of the supplied engine.
    """

    validate_engine = staticmethod(_validate_engine)
    _validate_unique_columns = staticmethod(validate_unique_columns)

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

        Raises:
            ValueError: If any constructor argument fails validation. Validation
                errors are aggregated into a single exception message.
        """
        self._engine = engine
        self._table_name = table_name
        self._schema = schema

        self._validate()

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

    def _validate(self) -> None:
        """Validate all constructor arguments.

        Calls the public static validation methods and aggregates their error
        messages.

        Raises:
            ValueError: If one or more constructor arguments are invalid.
        """
        errors = []
        errors.extend(self.validate_engine(self._engine))
        errors.extend(self.validate_table_name(self._table_name))
        errors.extend(self.validate_schema(self._schema))

        if errors:
            raise ValueError("\n".join(errors))

    @staticmethod
    def validate_table_name(table_name: Any) -> list[str]:
        """Validate a database table name.

        Args:
            table_name: Object to validate as a non-empty string.

        Returns:
            An empty list when the table name is valid; otherwise, a list
            containing validation error messages.
        """
        errors = []
        if not isinstance(table_name, str) or not table_name.strip():
            errors.append("Table Name must be a non-empty string.")
        return errors

    @staticmethod
    def validate_schema(schema: Any | None) -> list[str]:
        """Validate an optional database schema name.

        Args:
            schema: Optional database schema name. ``None`` indicates that
                the database's default schema should be used.

        Returns:
            An empty list when the schema is valid; otherwise, a list
            containing validation error messages.
        """
        if schema is None:
            return []

        errors = []
        if not isinstance(schema, str) or not schema.strip():
            errors.append("Schema must be a non-empty string.")
        return errors

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
