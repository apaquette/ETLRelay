"""Integration tests for SQL source and sink round trips."""

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

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
    text,
)
from sqlalchemy.engine import Engine

from etlrelay.core import Batch
from etlrelay.sinks import SqlSink
from etlrelay.sources import SqlSource


def _create_transaction_records(engine: Engine) -> None:
    """Create and seed the common customer table in an isolated database/schema."""
    metadata = MetaData()
    Table(
        "transactions",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("description", String, nullable=False),
        Column("amount", Float, nullable=True),
    )

    metadata.create_all(engine)


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Iterator[Engine]:
    """Create a temporary SQLite database with a target table."""
    engine = create_engine(f"sqlite:///{tmp_path / 'sql_round_trip.db'}")

    try:
        _create_transaction_records(engine)
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def postgresql_engine() -> Iterator[Engine]:
    """Create a temporary PostgreSQL database with a target table."""
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
            _create_transaction_records(engine)
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


class TestSqlRoundTrip:
    def test_sql_sink_output_can_be_read_by_sql_source(
        self,
        sql_engine: Engine,
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

        sink = SqlSink(sql_engine, "transactions")
        sink.write([Batch(table=table)])

        source = SqlSource(
            sql_engine,
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
