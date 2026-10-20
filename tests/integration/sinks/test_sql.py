"""Integration tests for the SQL sink."""

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest
from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
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


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Iterator[Engine]:
    """Create a temporary SQLite database with an existing customers table."""
    engine = create_engine(f"sqlite:///{tmp_path / 'sql_sink.db'}")
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
        connection.execute(
            customers.insert(),
            [{"id": 1, "name": "Existing", "score": 1.5}],
        )

    try:
        yield engine
    finally:
        engine.dispose()


def make_batch(rows: list[dict[str, Any]]) -> Batch:
    """Create an Arrow-backed batch from row dictionaries."""
    return Batch(table=pa.Table.from_pylist(rows))


def read_customers(engine: Engine) -> list[dict[str, Any]]:
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


def test_write_inserts_rows_and_preserves_nulls(sqlite_engine: Engine) -> None:
    """Append rows to the real target table while preserving their values."""
    sink = SqlSink(sqlite_engine, "customers")

    sink.write(
        [
            make_batch(
                [
                    {"id": 2, "name": "Alice", "score": 9.5},
                    {"id": 3, "name": "Bob", "score": None},
                ]
            )
        ]
    )

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
        {"id": 2, "name": "Alice", "score": 9.5},
        {"id": 3, "name": "Bob", "score": None},
    ]


def test_write_appends_across_separate_calls(sqlite_engine: Engine) -> None:
    """Preserve existing records when the sink is used repeatedly."""
    sink = SqlSink(sqlite_engine, "customers")

    sink.write([make_batch([{"id": 2, "name": "Alice", "score": 9.5}])])
    sink.write([make_batch([{"id": 3, "name": "Bob", "score": 7.0}])])

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
        {"id": 2, "name": "Alice", "score": 9.5},
        {"id": 3, "name": "Bob", "score": 7.0},
    ]


def test_write_skips_zero_row_batch(sqlite_engine: Engine) -> None:
    """Leave the database unchanged when the batch has no rows."""
    sink = SqlSink(sqlite_engine, "customers")
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

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
    ]


def test_write_rejects_unknown_batch_columns(sqlite_engine: Engine) -> None:
    """Reject columns that do not exist in the reflected target table."""
    sink = SqlSink(sqlite_engine, "customers")

    with pytest.raises(ValueError, match="columns not present"):
        sink.write(
            [
                make_batch(
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

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
    ]


def test_write_propagates_missing_table_error(sqlite_engine: Engine) -> None:
    """Raise NoSuchTableError when the destination table does not exist."""
    sink = SqlSink(sqlite_engine, "missing_customers")

    with pytest.raises(NoSuchTableError):
        sink.write([make_batch([{"id": 2, "name": "Alice", "score": 9.5}])])


def test_failed_batch_rolls_back_all_rows(sqlite_engine: Engine) -> None:
    """Roll back all rows in a batch after a constraint violation."""
    sink = SqlSink(sqlite_engine, "customers")

    with pytest.raises(IntegrityError):
        sink.write(
            [
                make_batch(
                    [
                        {"id": 2, "name": "Must roll back", "score": 2.0},
                        {"id": 1, "name": "Duplicate ID", "score": 3.0},
                        {"id": 3, "name": "Must also roll back", "score": 4.0},
                    ]
                )
            ]
        )

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
    ]


def test_previous_batch_commit_survives_later_batch_failure(
    sqlite_engine: Engine,
) -> None:
    """Keep an earlier batch committed when a later batch fails."""
    sink = SqlSink(sqlite_engine, "customers")

    with pytest.raises(IntegrityError):
        sink.write(
            [
                make_batch([{"id": 2, "name": "Committed", "score": 2.0}]),
                make_batch(
                    [
                        {"id": 3, "name": "Must roll back", "score": 3.0},
                        {"id": 1, "name": "Duplicate ID", "score": 4.0},
                    ]
                ),
            ]
        )

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
        {"id": 2, "name": "Committed", "score": 2.0},
    ]


def test_write_targets_configured_schema() -> None:
    """Write to the configured SQLite schema instead of the default schema."""
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
            connection.execute(
                main_customers.insert(),
                [{"id": 1, "name": "Main"}],
            )
            connection.execute(
                archive_customers.insert(),
                [{"id": 10, "name": "Archive"}],
            )

        sink = SqlSink(engine, "customers", schema="archive")
        sink.write([make_batch([{"id": 11, "name": "New archive row"}])])

        with engine.connect() as connection:
            main_rows = [
                dict(row)
                for row in connection.execute(
                    select(main_customers).order_by(main_customers.c.id)
                ).mappings()
            ]
            archive_rows = [
                dict(row)
                for row in connection.execute(
                    select(archive_customers).order_by(archive_customers.c.id)
                ).mappings()
            ]

        assert main_rows == [{"id": 1, "name": "Main"}]
        assert archive_rows == [
            {"id": 10, "name": "Archive"},
            {"id": 11, "name": "New archive row"},
        ]
    finally:
        event.remove(engine, "connect", attach_archive)
        engine.dispose()


def test_write_does_not_execute_sql_embedded_in_table_name(
    sqlite_engine: Engine,
) -> None:
    """Treat SQL-looking table names as identifiers, not SQL statements."""
    sink = SqlSink(
        sqlite_engine,
        "customers; DROP TABLE customers; --",
    )

    batch = make_batch([{"id": 2, "name": "Alice", "score": 9.5}])

    with pytest.raises(NoSuchTableError):
        sink.write([batch])

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
    ]


def test_write_treats_sql_looking_values_as_data(
    sqlite_engine: Engine,
) -> None:
    """Insert SQL-looking strings without interpreting them as SQL."""
    malicious_looking_value = "Alice'); DROP TABLE customers; --"

    sink = SqlSink(sqlite_engine, "customers")

    sink.write(
        [
            make_batch(
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

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
        {
            "id": 2,
            "name": malicious_looking_value,
            "score": 9.5,
        },
    ]


def test_write_supports_identifiers_requiring_quoting(
    sqlite_engine: Engine,
) -> None:
    """Write to tables and columns whose identifiers require quoting."""
    metadata = MetaData()

    records = Table(
        "customer records",
        metadata,
        Column("record id", Integer, primary_key=True),
        Column("display name", String, nullable=False),
    )

    metadata.create_all(sqlite_engine)

    sink = SqlSink(sqlite_engine, "customer records")

    sink.write(
        [
            make_batch(
                [
                    {
                        "record id": 1,
                        "display name": "Alice",
                    }
                ]
            )
        ]
    )

    with sqlite_engine.connect() as connection:
        rows = [dict(row) for row in connection.execute(select(records)).mappings()]

    assert rows == [
        {"record id": 1, "display name": "Alice"},
    ]


def test_write_logs_committed_batches_without_record_values(
    sqlite_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Log successful commits without exposing batch contents."""
    secret = "private-customer-value"

    sink = SqlSink(sqlite_engine, "customers")

    with caplog.at_level(logging.DEBUG, logger="etlrelay.sinks.sql"):
        sink.write(
            [
                make_batch(
                    [
                        {
                            "id": 2,
                            "name": secret,
                            "score": 9.5,
                        },
                        {
                            "id": 3,
                            "name": "Another customer",
                            "score": 7.0,
                        },
                    ]
                )
            ]
        )

    messages = [record.message for record in caplog.records if record.name == "etlrelay.sinks.sql"]

    assert messages == ["SQL sink committed batch (2 rows)."]
    assert secret not in caplog.text

    assert len(read_customers(sqlite_engine)) == 3


def test_write_logs_only_successfully_committed_batches(
    sqlite_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Do not log a successful commit for a rolled-back batch."""
    sink = SqlSink(sqlite_engine, "customers")

    first_batch = make_batch([{"id": 2, "name": "Committed", "score": 2.0}])
    second_batch = make_batch(
        [
            {"id": 3, "name": "Rolled back", "score": 3.0},
            {"id": 1, "name": "Duplicate ID", "score": 4.0},
        ]
    )

    with caplog.at_level(logging.DEBUG, logger="etlrelay.sinks.sql"):
        with pytest.raises(IntegrityError):
            sink.write([first_batch, second_batch])

    messages = [record.message for record in caplog.records if record.name == "etlrelay.sinks.sql"]

    assert messages == ["SQL sink committed batch (1 rows)."]

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
        {"id": 2, "name": "Committed", "score": 2.0},
    ]
