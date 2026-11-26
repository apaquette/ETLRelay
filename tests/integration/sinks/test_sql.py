"""Integration tests for the SQL sink."""

import logging
import os
from collections.abc import Iterator
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import pyarrow as pa
import pytest
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    Time,
    create_engine,
    event,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, NoSuchTableError
from sqlalchemy.pool import StaticPool

from etlrelay.core import Batch
from etlrelay.sinks import SqlSink

_CUSTOMER_RECORDS = [
    {"id": 1, "name": "Existing", "score": 1.5},
]


def _create_customer_records(engine: Engine) -> None:
    """Create and seed the common customer table in an isolated database/schema."""
    metadata = MetaData()
    customers = Table(
        "customers",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String, nullable=False),
        Column("score", Float, nullable=True),
    )

    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(customers.insert(), _CUSTOMER_RECORDS)


def _make_batch(rows: list[dict[str, Any]]) -> Batch:
    """Create an Arrow-backed batch from row dictionaries."""
    return Batch(table=pa.Table.from_pylist(rows))


def _read_customers(engine: Engine) -> list[dict[str, Any]]:
    """Read customers in deterministic ID order."""
    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT id, name, score
                FROM customers
                ORDER BY id
                """
            )
        )
        return [dict(row) for row in result.mappings()]


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Iterator[Engine]:
    """Create a temporary SQLite database with the common customer record."""
    engine = create_engine(f"sqlite:///{tmp_path / 'sql_sink.db'}")
    try:
        _create_customer_records(engine)
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def postgresql_engine() -> Iterator[Engine]:
    """Create a PostgreSQL engine isolated to a unique schema for this test."""
    postgres_url = os.environ.get("ETLRELAY_TEST_POSTGRES_URL")
    if not postgres_url:
        pytest.skip("ETLRELAY_TEST_POSTGRES_URL is not set")

    admin_engine = create_engine(postgres_url)
    schema = f"etlrelay_test_{uuid4().hex}"
    schema_created = False
    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        schema_created = True

        engine = create_engine(
            postgres_url,
            connect_args={"options": f"-c search_path={schema}"},
        )
        try:
            _create_customer_records(engine)
            yield engine
        finally:
            engine.dispose()
    finally:
        try:
            if schema_created:
                with admin_engine.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        finally:
            admin_engine.dispose()


@pytest.fixture(params=("sqlite_engine", "postgresql_engine"), ids=("sqlite", "postgresql"))
def sql_engine(request: pytest.FixtureRequest) -> Engine:
    """Run shared SQL sink tests against each configured database engine."""
    return request.getfixturevalue(request.param)


class TestSqlSink:
    def test_write_inserts_rows_and_preserves_nulls(self, sql_engine: Engine) -> None:
        """Append rows to the real target table while preserving their values."""
        sink = SqlSink(sql_engine, "customers")

        sink.write(
            [
                _make_batch(
                    [
                        {"id": 2, "name": "Alice", "score": 9.5},
                        {"id": 3, "name": "Bob", "score": None},
                    ]
                )
            ]
        )

        assert _read_customers(sql_engine) == [
            {"id": 1, "name": "Existing", "score": 1.5},
            {"id": 2, "name": "Alice", "score": 9.5},
            {"id": 3, "name": "Bob", "score": None},
        ]

    def test_write_appends_across_separate_calls(self, sql_engine: Engine) -> None:
        """Preserve existing records when the sink is used repeatedly."""
        sink = SqlSink(sql_engine, "customers")

        sink.write([_make_batch([{"id": 2, "name": "Alice", "score": 9.5}])])
        sink.write([_make_batch([{"id": 3, "name": "Bob", "score": 7.0}])])

        assert _read_customers(sql_engine) == [
            {"id": 1, "name": "Existing", "score": 1.5},
            {"id": 2, "name": "Alice", "score": 9.5},
            {"id": 3, "name": "Bob", "score": 7.0},
        ]

    def test_write_skips_zero_row_batch(self, sql_engine: Engine) -> None:
        """Leave the database unchanged when the batch has no rows."""
        sink = SqlSink(sql_engine, "customers")
        batch = Batch(
            table=pa.table(
                {
                    "id": pa.array([], type=pa.int64()),
                    "name": pa.array([], type=pa.string()),
                    "score": pa.array([], type=pa.float64()),
                }
            )
        )

        sink.write([batch])

        assert _read_customers(sql_engine) == [
            {"id": 1, "name": "Existing", "score": 1.5},
        ]

    def test_write_rejects_unknown_batch_columns(self, sql_engine: Engine) -> None:
        """Reject columns that do not exist in the reflected target table."""
        sink = SqlSink(sql_engine, "customers")

        with pytest.raises(ValueError, match="columns not present"):
            sink.write(
                [
                    _make_batch(
                        [
                            {
                                "id": 2,
                                "name": "Alice",
                                "score": 9.5,
                                "unexpected": "value",
                            }
                        ]
                    )
                ]
            )

        assert _read_customers(sql_engine) == [
            {"id": 1, "name": "Existing", "score": 1.5},
        ]

    def test_write_propagates_missing_table_error(self, sql_engine: Engine) -> None:
        """Raise NoSuchTableError when the destination table does not exist."""
        sink = SqlSink(sql_engine, "missing_customers")

        with pytest.raises(NoSuchTableError):
            sink.write([_make_batch([{"id": 2, "name": "Alice", "score": 9.5}])])

    def test_failed_batch_rolls_back_all_rows(self, sql_engine: Engine) -> None:
        """Roll back all rows in a batch after a constraint violation."""
        sink = SqlSink(sql_engine, "customers")

        with pytest.raises(IntegrityError):
            sink.write(
                [
                    _make_batch(
                        [
                            {"id": 2, "name": "Must roll back", "score": 2.0},
                            {"id": 1, "name": "Duplicate ID", "score": 3.0},
                            {"id": 3, "name": "Must also roll back", "score": 4.0},
                        ]
                    )
                ]
            )

        assert _read_customers(sql_engine) == [
            {"id": 1, "name": "Existing", "score": 1.5},
        ]

    def test_previous_batch_commit_survives_later_batch_failure(self, sql_engine: Engine) -> None:
        """Keep an earlier batch committed when a later batch fails."""
        sink = SqlSink(sql_engine, "customers")

        with pytest.raises(IntegrityError):
            sink.write(
                [
                    _make_batch([{"id": 2, "name": "Committed", "score": 2.0}]),
                    _make_batch(
                        [
                            {"id": 3, "name": "Must roll back", "score": 3.0},
                            {"id": 1, "name": "Duplicate ID", "score": 4.0},
                        ]
                    ),
                ]
            )

        # Reading through the same engine also verifies it remains usable after failure.
        assert _read_customers(sql_engine) == [
            {"id": 1, "name": "Existing", "score": 1.5},
            {"id": 2, "name": "Committed", "score": 2.0},
        ]

    def test_write_does_not_execute_sql_embedded_in_table_name(self, sql_engine: Engine) -> None:
        """Treat SQL-looking table names as identifiers, not SQL statements."""
        sink = SqlSink(
            sql_engine,
            "customers; DROP TABLE customers; --",
        )

        batch = _make_batch([{"id": 2, "name": "Alice", "score": 9.5}])

        with pytest.raises(NoSuchTableError):
            sink.write([batch])

        assert _read_customers(sql_engine) == [
            {"id": 1, "name": "Existing", "score": 1.5},
        ]

    def test_write_treats_sql_looking_values_as_data(self, sql_engine: Engine) -> None:
        """Insert SQL-looking strings without interpreting them as SQL."""
        malicious_looking_value = "Alice'); DROP TABLE customers; --"
        sink = SqlSink(sql_engine, "customers")

        sink.write(
            [
                _make_batch(
                    [
                        {
                            "id": 2,
                            "name": malicious_looking_value,
                            "score": 9.5,
                        }
                    ]
                )
            ]
        )

        assert _read_customers(sql_engine) == [
            {"id": 1, "name": "Existing", "score": 1.5},
            {
                "id": 2,
                "name": malicious_looking_value,
                "score": 9.5,
            },
        ]

    def test_write_supports_identifiers_requiring_quoting(self, sql_engine: Engine) -> None:
        """Write to tables and columns whose identifiers require quoting."""
        metadata = MetaData()
        records = Table(
            "customer records",
            metadata,
            Column("record id", Integer, primary_key=True),
            Column("display name", String, nullable=False),
        )

        metadata.create_all(sql_engine)

        sink = SqlSink(sql_engine, "customer records")
        sink.write(
            [
                _make_batch(
                    [
                        {
                            "record id": 1,
                            "display name": "Alice",
                        }
                    ]
                )
            ]
        )

        with sql_engine.connect() as connection:
            rows = [dict(row) for row in connection.execute(select(records)).mappings()]

        assert rows == [
            {"record id": 1, "display name": "Alice"},
        ]

    def test_write_logs_committed_batches_without_record_values(
        self,
        sql_engine: Engine,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Log successful commits without exposing batch contents."""
        secret = "private-customer-value"
        sink = SqlSink(sql_engine, "customers")

        with caplog.at_level(logging.DEBUG, logger="etlrelay.sinks.sql"):
            sink.write(
                [
                    _make_batch(
                        [
                            {"id": 2, "name": secret, "score": 9.5},
                            {"id": 3, "name": "Another customer", "score": 7.0},
                        ]
                    )
                ]
            )

        messages = [
            record.message for record in caplog.records if record.name == "etlrelay.sinks.sql"
        ]

        assert messages == ["SQL sink committed batch (2 rows)."]
        assert secret not in caplog.text
        assert len(_read_customers(sql_engine)) == 3

    def test_write_logs_only_successfully_committed_batches(
        self,
        sql_engine: Engine,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Do not log a successful commit for a rolled-back batch."""
        sink = SqlSink(sql_engine, "customers")
        first_batch = _make_batch([{"id": 2, "name": "Committed", "score": 2.0}])
        second_batch = _make_batch(
            [
                {"id": 3, "name": "Rolled back", "score": 3.0},
                {"id": 1, "name": "Duplicate ID", "score": 4.0},
            ]
        )

        with caplog.at_level(logging.DEBUG, logger="etlrelay.sinks.sql"):
            with pytest.raises(IntegrityError):
                sink.write([first_batch, second_batch])

        messages = [
            record.message for record in caplog.records if record.name == "etlrelay.sinks.sql"
        ]

        assert messages == ["SQL sink committed batch (1 rows)."]
        assert _read_customers(sql_engine) == [
            {"id": 1, "name": "Existing", "score": 1.5},
            {"id": 2, "name": "Committed", "score": 2.0},
        ]


class TestPostgresql:
    def test_write_targets_schema_qualified_table_with_quoted_identifiers(
        self,
        postgresql_engine: Engine,
    ) -> None:
        """Write to a schema-qualified table with reserved and mixed-case identifiers."""
        with postgresql_engine.connect() as connection:
            schema_name = connection.scalar(text("SELECT current_schema()"))

        assert schema_name is not None

        metadata = MetaData()
        records = Table(
            "Order",
            metadata,
            Column("RecordID", Integer, primary_key=True),
            Column("DisplayName", String, nullable=False),
            schema=schema_name,
        )
        metadata.create_all(postgresql_engine)

        sink = SqlSink(postgresql_engine, "Order", schema=schema_name)
        sink.write(
            [
                _make_batch(
                    [
                        {
                            "RecordID": 1,
                            "DisplayName": "PostgreSQL record",
                        }
                    ]
                )
            ]
        )

        with postgresql_engine.connect() as connection:
            rows = [dict(row) for row in connection.execute(select(records)).mappings()]

        assert rows == [
            {"RecordID": 1, "DisplayName": "PostgreSQL record"},
        ]

    def test_write_maps_arrow_values_to_postgresql_data_types(
        self,
        postgresql_engine: Engine,
    ) -> None:
        """Write Arrow values into representative PostgreSQL column types."""
        metadata = MetaData()
        typed_records = Table(
            "typed_records",
            metadata,
            Column("smallint_value", SmallInteger, nullable=False),
            Column("integer_value", Integer, nullable=False),
            Column("bigint_value", BigInteger, nullable=False),
            Column("real_value", Float(precision=24), nullable=False),
            Column("double_value", Float(precision=53), nullable=False),
            Column("numeric_value", Numeric(7, 2), nullable=False),
            Column("boolean_value", Boolean, nullable=False),
            Column("text_value", Text, nullable=False),
            Column("varchar_value", String(20), nullable=False),
            Column("date_value", Date, nullable=False),
            Column("time_value", Time, nullable=False),
            Column("timestamp_value", DateTime(timezone=False), nullable=False),
            Column("timestamptz_value", DateTime(timezone=True), nullable=False),
            Column("null_value", Integer, nullable=True),
        )
        metadata.create_all(postgresql_engine)

        values = {
            "smallint_value": pa.array([1], type=pa.int16()),
            "integer_value": pa.array([2], type=pa.int32()),
            "bigint_value": pa.array([3], type=pa.int64()),
            "real_value": pa.array([1.25], type=pa.float32()),
            "double_value": pa.array([2.5], type=pa.float64()),
            "numeric_value": pa.array([Decimal("12345.67")], type=pa.decimal128(7, 2)),
            "boolean_value": pa.array([True], type=pa.bool_()),
            "text_value": pa.array(["text value"], type=pa.string()),
            "varchar_value": pa.array(["varchar value"], type=pa.string()),
            "date_value": pa.array([date(2026, 1, 2)], type=pa.date32()),
            "time_value": pa.array([time(3, 4, 5)], type=pa.time64("us")),
            "timestamp_value": pa.array(
                [datetime(2026, 1, 2, 3, 4, 5)],
                type=pa.timestamp("us"),
            ),
            "timestamptz_value": pa.array(
                [datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)],
                type=pa.timestamp("us", tz="UTC"),
            ),
            "null_value": pa.array([None], type=pa.int64()),
        }

        sink = SqlSink(postgresql_engine, "typed_records")
        sink.write([Batch(table=pa.table(values))])

        with postgresql_engine.connect() as connection:
            row = connection.execute(select(typed_records)).mappings().one()

        assert dict(row) == {
            "smallint_value": 1,
            "integer_value": 2,
            "bigint_value": 3,
            "real_value": 1.25,
            "double_value": 2.5,
            "numeric_value": Decimal("12345.67"),
            "boolean_value": True,
            "text_value": "text value",
            "varchar_value": "varchar value",
            "date_value": date(2026, 1, 2),
            "time_value": time(3, 4, 5),
            "timestamp_value": datetime(2026, 1, 2, 3, 4, 5),
            "timestamptz_value": datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
            "null_value": None,
        }

    @pytest.mark.parametrize("should_fail", [False, True], ids=["success", "failure"])
    def test_write_returns_connection_to_pool(
        self,
        postgresql_engine: Engine,
        should_fail: bool,
    ) -> None:
        """Return checked-out PostgreSQL connections to the pool after writes."""
        events: list[str] = []

        def checkout(*_args: object) -> None:
            events.append("checkout")

        def checkin(*_args: object) -> None:
            events.append("checkin")

        event.listen(postgresql_engine, "checkout", checkout)
        event.listen(postgresql_engine, "checkin", checkin)

        try:
            sink = SqlSink(postgresql_engine, "customers")
            if should_fail:
                with pytest.raises(IntegrityError):
                    sink.write([_make_batch([{"id": 1, "name": "Duplicate", "score": 2.0}])])
            else:
                sink.write([_make_batch([{"id": 2, "name": "New customer", "score": 2.0}])])

            assert events
            assert events.count("checkout") == events.count("checkin")
        finally:
            event.remove(postgresql_engine, "checkout", checkout)
            event.remove(postgresql_engine, "checkin", checkin)


class TestSqlite:
    def test_write_targets_configured_schema(self) -> None:
        """Write to the configured SQLite attached-database schema."""
        engine = create_engine("sqlite://", poolclass=StaticPool)

        def attach_archive(
            dbapi_connection: Any,
            _connection_record: Any,
        ) -> None:
            """Attach an in-memory database as the archive schema."""
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("ATTACH DATABASE ':memory:' AS archive")
            finally:
                cursor.close()

        event.listen(engine, "connect", attach_archive)

        metadata = MetaData()
        main_customers = Table(
            "customers",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String, nullable=False),
        )
        archive_customers = Table(
            "customers",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String, nullable=False),
            schema="archive",
        )

        try:
            metadata.create_all(engine)

            with engine.begin() as connection:
                connection.execute(main_customers.insert(), [{"id": 1, "name": "Main"}])
                connection.execute(archive_customers.insert(), [{"id": 10, "name": "Archive"}])

            sink = SqlSink(engine, "customers", schema="archive")
            sink.write([_make_batch([{"id": 11, "name": "New archive row"}])])

            with engine.connect() as connection:
                main_result = connection.execute(
                    select(main_customers).order_by(main_customers.c.id)
                )
                main_rows = [dict(row) for row in main_result.mappings()]
                archive_result = connection.execute(
                    select(archive_customers).order_by(archive_customers.c.id)
                )
                archive_rows = [dict(row) for row in archive_result.mappings()]

            assert main_rows == [{"id": 1, "name": "Main"}]
            assert archive_rows == [
                {"id": 10, "name": "Archive"},
                {"id": 11, "name": "New archive row"},
            ]
        finally:
            event.remove(engine, "connect", attach_archive)
            engine.dispose()
