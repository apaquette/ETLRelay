"""Unit tests for the SQL sink."""

from collections.abc import Iterator
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
def sqlite_engine() -> Iterator[Engine]:
    """Create an in-memory SQLite database with sample customer data."""
    engine = create_engine("sqlite:///:memory:")
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
    """Create a batch from dictionaries representing rows."""
    return Batch(table=pa.Table.from_pylist(rows))


def read_customers(engine: Engine) -> list[dict[str, Any]]:
    """Return all customer rows ordered by ID."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT id, name, score FROM customers ORDER BY id"))
        return [dict(row) for row in result.mappings()]


def test_write_inserts_rows_with_values_preserved(
    sqlite_engine: Engine,
) -> None:
    """Insert rows while preserving values and nulls."""
    sink = SqlSink(sqlite_engine, "customers")

    sink.write(
        [
            make_batch(
                [
                    {"id": 2, "name": "Alice", "score": 9.5},
                    {"id": 3, "name": "Bob", "score": None},
                    {"id": 4, "name": "Charlie", "score": 7.0},
                ]
            )
        ]
    )

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
        {"id": 2, "name": "Alice", "score": 9.5},
        {"id": 3, "name": "Bob", "score": None},
        {"id": 4, "name": "Charlie", "score": 7.0},
    ]


def test_multiple_writes_append_without_replacing_rows(
    sqlite_engine: Engine,
) -> None:
    """Append rows across separate writes without replacing existing data."""
    sink = SqlSink(sqlite_engine, "customers")

    sink.write([make_batch([{"id": 2, "name": "Alice", "score": 9.5}])])
    sink.write([make_batch([{"id": 3, "name": "Bob", "score": 7.0}])])

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
        {"id": 2, "name": "Alice", "score": 9.5},
        {"id": 3, "name": "Bob", "score": 7.0},
    ]


def test_empty_batch_is_a_no_op(sqlite_engine: Engine) -> None:
    """Complete successfully without inserting rows for an empty batch."""
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


def test_write_supports_quoted_table_and_column_identifiers(
    sqlite_engine: Engine,
) -> None:
    """Support table and column identifiers requiring SQL quoting."""
    metadata = MetaData()
    unusual_table = Table(
        "order details",
        metadata,
        Column("select", Integer, primary_key=True),
        Column("customer name", String, nullable=False),
    )
    metadata.create_all(sqlite_engine)

    sink = SqlSink(sqlite_engine, "order details")
    sink.write([make_batch([{"select": 7, "customer name": "Alice"}])])

    with sqlite_engine.connect() as connection:
        result = connection.execute(select(unusual_table).order_by(unusual_table.c["select"]))
        rows = [dict(row) for row in result.mappings()]

    assert rows == [{"select": 7, "customer name": "Alice"}]


def test_table_name_is_treated_as_an_identifier(
    sqlite_engine: Engine,
) -> None:
    """Do not execute SQL contained in a caller-supplied table name."""
    malicious_name = "customers; DROP TABLE customers; --"

    with pytest.raises(NoSuchTableError):
        sink = SqlSink(sqlite_engine, malicious_name)
        sink.write([make_batch([{"id": 2, "name": "Alice", "score": 9.5}])])

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
    ]


def test_write_raises_for_missing_table(sqlite_engine: Engine) -> None:
    """Raise a clear error when the target table does not exist."""
    with pytest.raises(NoSuchTableError):
        sink = SqlSink(sqlite_engine, "missing_customers")
        sink.write([make_batch([{"id": 2, "name": "Alice", "score": 9.5}])])


def test_write_rejects_unknown_batch_columns(
    sqlite_engine: Engine,
) -> None:
    """Reject batch columns that are absent from the target table."""
    sink = SqlSink(sqlite_engine, "customers")

    with pytest.raises(ValueError, match="(?i)column"):
        sink.write(
            [
                make_batch(
                    [
                        {
                            "id": 2,
                            "name": "Alice",
                            "score": 9.5,
                            "unrecognized": "unexpected",
                        }
                    ]
                )
            ]
        )

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
    ]


def test_failed_batch_rolls_back_all_rows(
    sqlite_engine: Engine,
) -> None:
    """Roll back every insertion from a batch that violates a constraint."""
    sink = SqlSink(sqlite_engine, "customers")
    batch = make_batch(
        [
            {"id": 2, "name": "Would be inserted", "score": 2.0},
            {"id": 1, "name": "Duplicate ID", "score": 3.0},
            {"id": 3, "name": "Must also be rolled back", "score": 4.0},
        ]
    )

    with pytest.raises(IntegrityError):
        sink.write([batch])

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
    ]


def test_committed_batches_survive_a_later_batch_failure(
    sqlite_engine: Engine,
) -> None:
    """Keep earlier batches committed when a subsequent batch fails."""
    sink = SqlSink(sqlite_engine, "customers")
    batches = [
        make_batch([{"id": 2, "name": "Committed", "score": 2.0}]),
        make_batch(
            [
                {"id": 3, "name": "Must be rolled back", "score": 3.0},
                {"id": 1, "name": "Duplicate ID", "score": 4.0},
            ]
        ),
    ]

    with pytest.raises(IntegrityError):
        sink.write(batches)

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
        {"id": 2, "name": "Committed", "score": 2.0},
    ]


@pytest.mark.parametrize("should_fail", [False, True], ids=["success", "failure"])
def test_connections_are_returned_to_pool(
    sqlite_engine: Engine,
    should_fail: bool,
) -> None:
    """Return database connections to the pool after success or failure."""
    sink = SqlSink(sqlite_engine, "customers")

    if should_fail:
        batch = make_batch(
            [
                {"id": 2, "name": "Would be rolled back", "score": 2.0},
                {"id": 1, "name": "Duplicate ID", "score": 3.0},
            ]
        )
    else:
        batch = make_batch([{"id": 2, "name": "Successful insert", "score": 2.0}])

    counts = {"checkout": 0, "checkin": 0}

    def on_checkout(*_: Any) -> None:
        counts["checkout"] += 1

    def on_checkin(*_: Any) -> None:
        counts["checkin"] += 1

    pool = sqlite_engine.pool
    event.listen(pool, "checkout", on_checkout)
    event.listen(pool, "checkin", on_checkin)

    try:
        if should_fail:
            with pytest.raises(IntegrityError):
                sink.write([batch])
        else:
            sink.write([batch])
    finally:
        event.remove(pool, "checkout", on_checkout)
        event.remove(pool, "checkin", on_checkin)

    assert counts["checkout"] >= 1
    assert counts["checkin"] == counts["checkout"]


def test_write_rejects_duplicate_batch_columns(
    sqlite_engine: Engine,
) -> None:
    """Reject batches containing duplicate column names."""
    sink = SqlSink(sqlite_engine, "customers")
    table = pa.Table.from_arrays(
        [
            pa.array([2], type=pa.int64()),
            pa.array([3], type=pa.int64()),
        ],
        names=["id", "id"],
    )
    batch = Batch(table=table)

    with pytest.raises(ValueError, match="duplicate column names"):
        sink.write([batch])

    assert read_customers(sqlite_engine) == [
        {"id": 1, "name": "Existing", "score": 1.5},
    ]


def test_write_inserts_into_specified_schema() -> None:
    """Write to the configured schema when tables share the same name."""
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    def attach_archive(
        dbapi_connection: Any,
        _connection_record: Any,
    ) -> None:
        """Attach a separate in-memory SQLite database."""
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS archive")

    event.listen(engine, "connect", attach_archive)

    metadata = MetaData()

    main_customers = Table(
        "customers",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String, nullable=False),
        Column("score", Float, nullable=True),
    )

    archive_customers = Table(
        "customers",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String, nullable=False),
        Column("score", Float, nullable=True),
        schema="archive",
    )

    try:
        metadata.create_all(engine)

        with engine.begin() as connection:
            connection.execute(
                main_customers.insert(),
                [{"id": 1, "name": "Main", "score": 1.0}],
            )
            connection.execute(
                archive_customers.insert(),
                [{"id": 10, "name": "Archived", "score": 10.0}],
            )

        sink = SqlSink(
            engine,
            "customers",
            schema="archive",
        )
        sink.write([make_batch([{"id": 11, "name": "New archive row", "score": 11.0}])])

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

        assert main_rows == [
            {"id": 1, "name": "Main", "score": 1.0},
        ]
        assert archive_rows == [
            {"id": 10, "name": "Archived", "score": 10.0},
            {"id": 11, "name": "New archive row", "score": 11.0},
        ]
    finally:
        event.remove(engine, "connect", attach_archive)
        engine.dispose()
