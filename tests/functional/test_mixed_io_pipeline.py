"""Functional tests for pipelines combining file and SQL components."""

from collections.abc import Iterator
from pathlib import Path

import pyarrow.csv as pacsv
import pytest
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, create_engine
from sqlalchemy.engine import Engine

from etlrelay.pipeline import Pipeline
from etlrelay.processors import FilterRows
from etlrelay.readers import CsvReader
from etlrelay.security import PathValidator
from etlrelay.sinks import FileSink, SqlSink
from etlrelay.sources import FileSource, SqlSource
from etlrelay.storage import LocalFileSystem
from etlrelay.writers import CsvWriter


@pytest.fixture
def local_storage(tmp_path: Path) -> LocalFileSystem:
    """Create filesystem storage restricted to the test directory."""
    return LocalFileSystem(
        path_validator=PathValidator(base_path=tmp_path),
    )


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Iterator[Engine]:
    """Create a temporary SQLite database with source and target tables."""
    engine = create_engine(f"sqlite:///{tmp_path / 'mixed_io.db'}")
    metadata = MetaData()

    Table(
        "source_records",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("category", String, nullable=False),
        Column("amount", Float, nullable=True),
    )

    Table(
        "processed_records",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("category", String, nullable=False),
        Column("amount", Float, nullable=True),
    )

    metadata.create_all(engine)

    try:
        yield engine
    finally:
        engine.dispose()


class TestMixedIoPipeline:
    def test_csv_source_to_sql_sink(
        self,
        tmp_path: Path,
        local_storage: LocalFileSystem,
        sqlite_engine: Engine,
    ) -> None:
        """Read CSV records, filter them, and append them to SQL."""
        input_path = tmp_path / "input.csv"
        input_path.write_text(
            "id,category,amount\n1,include,12.5\n2,exclude,20.0\n3,include,30.0\n",
            encoding="utf-8",
        )

        source = FileSource(
            path="input.csv",
            storage=local_storage,
            reader=CsvReader(),
        )
        processor = FilterRows(
            column="category",
            operator="==",
            value="include",
        )
        sink = SqlSink(sqlite_engine, "processed_records")

        pipeline = Pipeline(source, [processor], sink)
        pipeline.run()

        sql_source = SqlSource(
            sqlite_engine,
            """
            SELECT id, category, amount
            FROM processed_records
            ORDER BY id
            """,
        )
        batches = list(sql_source.read())

        assert len(batches) == 1
        assert batches[0].table.to_pylist() == [
            {"id": 1, "category": "include", "amount": 12.5},
            {"id": 3, "category": "include", "amount": 30.0},
        ]

    def test_sql_source_to_csv_sink(
        self,
        tmp_path: Path,
        local_storage: LocalFileSystem,
        sqlite_engine: Engine,
    ) -> None:
        """Query SQL records, filter them, and write them to CSV."""
        with sqlite_engine.begin() as connection:
            connection.execute(
                Table(
                    "source_records",
                    MetaData(),
                    autoload_with=connection,
                ).insert(),
                [
                    {"id": 1, "category": "include", "amount": 12.5},
                    {"id": 2, "category": "exclude", "amount": 20.0},
                    {"id": 3, "category": "include", "amount": 30.0},
                ],
            )

        source = SqlSource(
            sqlite_engine,
            """
            SELECT id, category, amount
            FROM source_records
            ORDER BY id
            """,
        )
        processor = FilterRows(
            column="category",
            operator="==",
            value="include",
        )
        sink = FileSink(
            path="output.csv",
            storage=local_storage,
            writer=CsvWriter(),
        )

        pipeline = Pipeline(source, [processor], sink)
        pipeline.run()

        output_path = tmp_path / "output.csv"
        assert output_path.is_file()

        result = pacsv.read_csv(output_path)

        assert result.to_pylist() == [
            {"id": 1, "category": "include", "amount": 12.5},
            {"id": 3, "category": "include", "amount": 30.0},
        ]
