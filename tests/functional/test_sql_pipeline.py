"""Functional tests for SQL-backed pipelines."""

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    text,
)
from sqlalchemy.engine import Engine

from etlrelay.core import Batch
from etlrelay.pipeline import Pipeline
from etlrelay.processors import FilterRows
from etlrelay.sinks import SqlSink
from etlrelay.sources import SqlSource


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Iterator[Engine]:
    """Create a temporary SQLite database for SQL pipeline tests."""
    engine = create_engine(f"sqlite:///{tmp_path / 'sql_pipeline.db'}")
    metadata = MetaData()

    source_table = Table(
        "source_records",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("category", String, nullable=False),
        Column("score", Float, nullable=True),
    )

    Table(
        "processed_records",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("category", String, nullable=False),
        Column("score", Float, nullable=True),
    )

    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            source_table.insert(),
            [
                {"id": 1, "category": "include", "score": 9.5},
                {"id": 2, "category": "include", "score": 6.0},
                {"id": 3, "category": "exclude", "score": 10.0},
                {"id": 4, "category": "include", "score": 7.5},
            ],
        )

    try:
        yield engine
    finally:
        engine.dispose()


def read_processed_records(engine: Engine) -> list[dict[str, Any]]:
    """Read processed records in a deterministic order."""
    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT id, category, score
                FROM processed_records
                ORDER BY id
                """
            )
        )
        return [dict(row) for row in result.mappings()]


class RecordingProcessor:
    """Track processor calls while delegating actual transformations."""

    def __init__(self, processor: FilterRows) -> None:
        self._processor = processor
        self.calls = 0

    def process(self, batch: Batch) -> Batch:
        """Record the call and process the supplied batch."""
        self.calls += 1
        return self._processor.process(batch)


class RecordingSqlSink(SqlSink):
    """Record sink calls and batches while performing real SQL writes."""

    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, "processed_records")
        self.write_calls = 0
        self.received_batches: list[Batch] = []

    def write(self, batches: Iterable[Batch]) -> None:
        """Record the received batches and delegate to SqlSink."""
        self.write_calls += 1
        materialized_batches = list(batches)
        self.received_batches.extend(materialized_batches)
        super().write(materialized_batches)


def test_sql_pipeline_queries_transforms_and_writes_records(
    sqlite_engine: Engine,
) -> None:
    """Run a parameterized SQL source through a processor and SQL sink."""
    source = SqlSource(
        sqlite_engine,
        """
        SELECT id, category, score
        FROM source_records
        WHERE category = :category
        ORDER BY id
        """,
        parameters={"category": "include"},
    )
    processor = FilterRows(
        column="score",
        operator=">=",
        value=8.0,
    )
    sink = SqlSink(sqlite_engine, "processed_records")
    pipeline = Pipeline(source, [processor], sink)

    pipeline.run()

    assert read_processed_records(sqlite_engine) == [
        {"id": 1, "category": "include", "score": 9.5},
    ]


def test_empty_sql_source_does_not_process_or_invoke_sink(
    sqlite_engine: Engine,
) -> None:
    """An empty source result produces no processor or sink calls."""
    source = SqlSource(
        sqlite_engine,
        """
        SELECT id, category, score
        FROM source_records
        WHERE category = :category
        """,
        parameters={"category": "missing"},
    )
    processor = RecordingProcessor(FilterRows(column="score", operator=">=", value=8.0))
    sink = RecordingSqlSink(sqlite_engine)
    pipeline = Pipeline(source, [processor], sink)

    pipeline.run()

    assert processor.calls == 0
    assert sink.write_calls == 0
    assert sink.received_batches == []
    assert read_processed_records(sqlite_engine) == []


def test_zero_row_processed_batch_reaches_sink_without_inserting_rows(
    sqlite_engine: Engine,
) -> None:
    """A processed zero-row batch reaches the sink but inserts nothing."""
    source = SqlSource(
        sqlite_engine,
        """
        SELECT id, category, score
        FROM source_records
        WHERE category = :category
        ORDER BY id
        """,
        parameters={"category": "include"},
    )
    processor = RecordingProcessor(FilterRows(column="score", operator=">=", value=100.0))
    sink = RecordingSqlSink(sqlite_engine)
    pipeline = Pipeline(source, [processor], sink)

    pipeline.run()

    assert processor.calls == 1
    assert sink.write_calls == 1
    assert len(sink.received_batches) == 1
    assert sink.received_batches[0].table.num_rows == 0
    assert read_processed_records(sqlite_engine) == []
