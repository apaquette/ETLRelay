"""Unit tests for SqlSource."""

from collections.abc import Iterator

import pyarrow as pa
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from etlrelay.core import Batch, Source
from etlrelay.sources import SqlSource


def test_sql_source_satisfies_source_protocol(
    sqlite_engine: Engine,
) -> None:
    """SqlSource implements the Source protocol."""
    source = SqlSource(
        sqlite_engine,
        "SELECT id FROM customers",
    )

    assert isinstance(source, Source)


@pytest.fixture
def sqlite_engine() -> Iterator[Engine]:
    """Provide an in-memory SQLite database with representative data."""
    engine = create_engine("sqlite+pysqlite:///:memory:")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE customers (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    score REAL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO customers (id, name, score)
                VALUES (:id, :name, :score)
                """
            ),
            [
                {"id": 1, "name": "Alice", "score": 9.5},
                {"id": 2, "name": "Bob", "score": None},
                {"id": 3, "name": "Charlie", "score": 7.0},
            ],
        )

    try:
        yield engine
    finally:
        engine.dispose()


def test_read_returns_query_results_as_one_batch(
    sqlite_engine: Engine,
) -> None:
    """A query with rows produces one Arrow-backed Batch."""
    source = SqlSource(
        sqlite_engine,
        "SELECT id, name, score FROM customers ORDER BY id",
    )

    batches = list(source.read())

    assert len(batches) == 1
    assert isinstance(batches[0], Batch)

    table = batches[0].table

    assert isinstance(table, pa.Table)
    assert table.column_names == ["id", "name", "score"]
    assert table.num_rows == 3
    assert table.to_pylist() == [
        {"id": 1, "name": "Alice", "score": 9.5},
        {"id": 2, "name": "Bob", "score": None},
        {"id": 3, "name": "Charlie", "score": 7.0},
    ]


def test_read_preserves_arrow_compatible_column_types(
    sqlite_engine: Engine,
) -> None:
    """SQL values are converted to the expected Arrow types."""
    source = SqlSource(
        sqlite_engine,
        "SELECT id, name, score FROM customers ORDER BY id",
    )

    batch = list(source.read())[0]

    assert batch.table.schema.field("id").type == pa.int64()
    assert batch.table.schema.field("name").type == pa.string()
    assert batch.table.schema.field("score").type == pa.float64()


def test_read_returns_no_batches_for_empty_result(
    sqlite_engine: Engine,
) -> None:
    """An empty result produces no batches, not a zero-row Batch."""
    source = SqlSource(
        sqlite_engine,
        "SELECT id, name, score FROM customers WHERE id < 0",
    )

    assert source.read() == []


def test_read_supports_named_query_parameters(
    sqlite_engine: Engine,
) -> None:
    """Named parameters are passed separately from the SQL statement."""
    source = SqlSource(
        sqlite_engine,
        "SELECT id, name FROM customers WHERE name = :name",
        parameters={"name": "Bob"},
    )

    batches = list(source.read())

    assert len(batches) == 1
    assert batches[0].table.column_names == ["id", "name"]
    assert batches[0].table.to_pylist() == [
        {"id": 2, "name": "Bob"},
    ]


def test_parameter_values_cannot_change_query_structure(
    sqlite_engine: Engine,
) -> None:
    """SQL-looking input is treated as a value, not executable SQL."""
    source = SqlSource(
        sqlite_engine,
        "SELECT id, name FROM customers WHERE name = :name",
        parameters={"name": "Alice' OR 1=1 --"},
    )

    assert list(source.read()) == []


def test_read_rejects_duplicate_result_column_names(
    sqlite_engine: Engine,
) -> None:
    """Duplicate result names are rejected rather than silently lost."""
    source = SqlSource(
        sqlite_engine,
        """
        SELECT id AS value, name AS value
        FROM customers
        """,
    )

    with pytest.raises(
        ValueError,
        match="(?i)(column.*(duplicate|unique)|(duplicate|unique).*column)",
    ):
        source.read()


def test_read_closes_connections_before_returning(
    sqlite_engine: Engine,
) -> None:
    """The connection is returned before read() returns."""
    checkouts: list[object] = []
    checkins: list[object] = []

    def on_checkout(
        dbapi_connection: object,
        connection_record: object,
        connection_proxy: object,
    ) -> None:
        checkouts.append(connection_record)

    def on_checkin(
        dbapi_connection: object | None,
        connection_record: object,
    ) -> None:
        checkins.append(connection_record)

    pool = sqlite_engine.pool
    event.listen(pool, "checkout", on_checkout)
    event.listen(pool, "checkin", on_checkin)

    try:
        source = SqlSource(
            sqlite_engine,
            "SELECT id, name FROM customers ORDER BY id",
        )

        batches = source.read()

        # Resource cleanup has happened before read() returns.
        assert len(checkouts) == 1
        assert len(checkins) == 1
        assert len(list(batches)) == 1

        # The source did not dispose of the caller's engine.
        with sqlite_engine.connect() as connection:
            count = connection.execute(text("SELECT COUNT(*) FROM customers")).scalar_one()

        assert count == 3
    finally:
        event.remove(pool, "checkout", on_checkout)
        event.remove(pool, "checkin", on_checkin)


def test_read_propagates_sql_errors_and_releases_connection(
    sqlite_engine: Engine,
) -> None:
    """SQL errors propagate while the connection is returned to the pool."""
    checkouts: list[object] = []
    checkins: list[object] = []

    def on_checkout(
        dbapi_connection: object,
        connection_record: object,
        connection_proxy: object,
    ) -> None:
        checkouts.append(connection_record)

    def on_checkin(
        dbapi_connection: object | None,
        connection_record: object,
    ) -> None:
        checkins.append(connection_record)

    pool = sqlite_engine.pool
    event.listen(pool, "checkout", on_checkout)
    event.listen(pool, "checkin", on_checkin)

    try:
        source = SqlSource(
            sqlite_engine,
            "SELECT * FROM missing_customers",
        )

        with pytest.raises(SQLAlchemyError):
            source.read()

        assert len(checkouts) == 1
        assert len(checkins) == 1
    finally:
        event.remove(pool, "checkout", on_checkout)
        event.remove(pool, "checkin", on_checkin)
