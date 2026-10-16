"""Run a complete SQLAlchemy/SQLite pipeline using ETLRelay.

Run from the repository root after installing the project:
    uv run python examples/sqlite_pipeline.py

The example uses an in-memory database and contains no credentials.
"""
from __future__ import annotations

from sqlalchemy import Column, Float, Integer, MetaData, String, Table, create_engine

from etlrelay.pipeline import Pipeline
from etlrelay.processors import SelectColumns
from etlrelay.sinks import SqlSink
from etlrelay.sources import SqlSource


def main() -> None:
    # In-memory SQLite keeps the example self-contained and repeatable.
    engine = create_engine("sqlite://")
    try:
        metadata = MetaData()

        orders = Table(
            "orders",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("customer", String, nullable=False),
            Column("status", String, nullable=False),
            Column("total", Float, nullable=False),
        )
        Table(
            "processed_orders",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("customer", String, nullable=False),
            Column("total", Float, nullable=False),
        )
        metadata.create_all(engine)

        with engine.begin() as connection:
            connection.execute(
                orders.insert(),
                [
                    {"id": 1, "customer": "Avery", "status": "ready", "total": 18.5},
                    {"id": 2, "customer": "Riley", "status": "held", "total": 27.0},
                    {"id": 3, "customer": "Jordan", "status": "ready", "total": 42.25},
                ],
            )

        # Query values are bound through the parameters mapping, not formatted
        # into SQL text. The destination table already exists above; SqlSink
        # only appends to it and does not create or migrate tables.
        pipeline = Pipeline(
            source=SqlSource(
                engine,
                """
                SELECT id, customer, status, total
                FROM orders
                WHERE status = :status
                ORDER BY id
                """,
                parameters={"status": "ready"},
            ),
            processors=[SelectColumns(columns=["id", "customer", "total"])],
            sink=SqlSink(engine, "processed_orders"),
        )
        pipeline.run()

        results = list(
            SqlSource(
                engine,
                "SELECT id, customer, total FROM processed_orders ORDER BY id",
            ).read()
        )
        rows = results[0].table.to_pylist() if results else []
        print(rows)
    finally:
        # ETLRelay uses but does not dispose the caller-owned engine.
        engine.dispose()


if __name__ == "__main__":
    main()