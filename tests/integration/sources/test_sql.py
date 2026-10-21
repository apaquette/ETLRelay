"""Integration tests for the SQL source."""

import logging
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
from sqlalchemy.exc import SQLAlchemyError

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


def test_read_logs_row_count_without_query_parameters(
    sqlite_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Log the number of returned rows without logging SQL values."""
    secret = "private-database-credential"

    source = SqlSource(
        sqlite_engine,
        "SELECT :secret AS value",
        parameters={"secret": secret},
    )

    with caplog.at_level(logging.DEBUG, logger="etlrelay.sources.sql"):
        batches = list(source.read())

    messages = [
        record.message for record in caplog.records if record.name == "etlrelay.sources.sql"
    ]

    assert messages == ["SQL source read completed (1 rows)."]
    assert batches[0].table.to_pylist() == [{"value": secret}]
    assert secret not in caplog.text
    assert "SELECT :secret" not in caplog.text


def test_read_failure_does_not_log_query_or_parameters(
    sqlite_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Propagate SQL errors without logging statements or bound values."""
    secret = "private-query-parameter"

    source = SqlSource(
        sqlite_engine,
        "SELECT :secret FROM missing_table",
        parameters={"secret": secret},
    )

    with caplog.at_level(logging.DEBUG, logger="etlrelay.sources.sql"):
        with pytest.raises(SQLAlchemyError):
            source.read()

    messages = [
        record.message for record in caplog.records if record.name == "etlrelay.sources.sql"
    ]

    assert messages == []
    assert secret not in caplog.text
    assert "missing_table" not in caplog.text
