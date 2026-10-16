"""Integration tests for the SQL source."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)
from sqlalchemy.engine import Engine

from etlrelay.sources import SqlSource


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Iterator[Engine]:
    """Create a temporary SQLite database with source records."""
    engine = create_engine(f"sqlite:///{tmp_path / 'sql_source.db'}")
    metadata = MetaData()

    records = Table(
        "records",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("category", String, nullable=False),
        Column("score", Float, nullable=True),
    )

    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            records.insert(),
            [
                {"id": 1, "category": "include", "score": 9.5},
                {"id": 2, "category": "include", "score": None},
                {"id": 3, "category": "exclude", "score": 7.0},
            ],
        )

    try:
        yield engine
    finally:
        engine.dispose()


def test_read_queries_real_sqlite_records(sqlite_engine: Engine) -> None:
    """Execute a parameterized query and convert results to an Arrow batch."""
    source = SqlSource(
        sqlite_engine,
        """
        SELECT id, category, score
        FROM records
        WHERE category = :category
        ORDER BY id
        """,
        parameters={"category": "include"},
    )

    batches = list(source.read())

    assert len(batches) == 1
    assert batches[0].table.to_pylist() == [
        {"id": 1, "category": "include", "score": 9.5},
        {"id": 2, "category": "include", "score": None},
    ]


def test_read_returns_no_batches_for_empty_query_result(
    sqlite_engine: Engine,
) -> None:
    """Return no batches when the query finds no rows."""
    source = SqlSource(
        sqlite_engine,
        "SELECT id, category, score FROM records WHERE category = :category",
        parameters={"category": "missing"},
    )

    assert list(source.read()) == []


def test_read_binds_parameter_values_instead_of_interpolating_sql(
    sqlite_engine: Engine,
) -> None:
    """Treat SQL-looking input as a bound value, not executable SQL."""
    source = SqlSource(
        sqlite_engine,
        "SELECT id, category, score FROM records WHERE category = :category",
        parameters={"category": "include' OR 1=1 --"},
    )

    assert list(source.read()) == []


def test_read_rejects_duplicate_result_column_names(
    sqlite_engine: Engine,
) -> None:
    """Reject duplicate column names produced by a real SQLite query."""
    source = SqlSource(
        sqlite_engine,
        """
        SELECT id AS duplicate, category AS duplicate
        FROM records
        """,
    )

    with pytest.raises(ValueError, match="duplicate column names"):
        source.read()
