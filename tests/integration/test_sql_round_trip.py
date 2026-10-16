"""Integration tests for SQL source and sink round trips."""

from collections.abc import Iterator
from pathlib import Path

import pyarrow as pa
import pytest
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, create_engine
from sqlalchemy.engine import Engine

from etlrelay.core import Batch
from etlrelay.sinks import SqlSink
from etlrelay.sources import SqlSource


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Iterator[Engine]:
    """Create a temporary SQLite database with a target table."""
    engine = create_engine(f"sqlite:///{tmp_path / 'sql_round_trip.db'}")
    metadata = MetaData()

    Table(
        "transactions",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("description", String, nullable=False),
        Column("amount", Float, nullable=True),
    )

    metadata.create_all(engine)

    try:
        yield engine
    finally:
        engine.dispose()


class TestSqlRoundTrip:
    def test_sql_sink_output_can_be_read_by_sql_source(
        self,
        sqlite_engine: Engine,
    ) -> None:
        """Preserve values and nulls across a SQL sink/source round trip."""
        table = pa.table(
            {
                "id": pa.array([1, 2, 3], type=pa.int64()),
                "description": pa.array(
                    ["Payment", "Refund", "Transfer"],
                    type=pa.string(),
                ),
                "amount": pa.array(
                    [12.5, None, 30.0],
                    type=pa.float64(),
                ),
            }
        )

        sink = SqlSink(sqlite_engine, "transactions")
        sink.write([Batch(table=table)])

        source = SqlSource(
            sqlite_engine,
            """
            SELECT id, description, amount
            FROM transactions
            ORDER BY id
            """,
        )
        batches = list(source.read())

        assert len(batches) == 1

        result = batches[0].table

        assert result.column_names == table.column_names
        assert result.to_pylist() == table.to_pylist()
        assert result.schema.equals(table.schema, check_metadata=False)
