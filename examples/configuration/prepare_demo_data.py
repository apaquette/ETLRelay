"""Create local CSV, Parquet, and SQLite input/output data for config examples."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

DATA_DIR = Path("examples/configuration/data")
ROWS = [
    {"id": 1, "amount": 18.5, "state": "ready"},
    {"id": 2, "amount": 27.0, "state": "ready"},
    {"id": 3, "amount": 0.0, "state": "ready"},
    {"id": 4, "amount": -4.0, "state": "ready"},
]


def main() -> None:
    """Recreate the demo input files and SQLite tables from scratch."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = DATA_DIR / "input.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["id", "amount", "state"])
        writer.writeheader()
        writer.writerows(ROWS)

    table = pa.Table.from_pylist(ROWS)
    pq.write_table(table, DATA_DIR / "input.parquet")

    source_db = DATA_DIR / "source.db"
    with sqlite3.connect(source_db) as connection:
        connection.execute("DROP TABLE IF EXISTS source_records")
        connection.execute(
            """CREATE TABLE source_records (
                id INTEGER NOT NULL,
                amount REAL NOT NULL,
                state TEXT NOT NULL
            )"""
        )
        connection.executemany(
            "INSERT INTO source_records (id, amount, state) VALUES (?, ?, ?)",
            [(row["id"], row["amount"], row["state"]) for row in ROWS],
        )

    sink_db = DATA_DIR / "sink.db"
    with sqlite3.connect(sink_db) as connection:
        connection.execute("DROP TABLE IF EXISTS processed_records")
        connection.execute(
            """CREATE TABLE processed_records (
                record_id INTEGER NOT NULL,
                amount REAL NOT NULL
            )"""
        )

    print(f"Prepared demo data in {DATA_DIR.resolve()}")


if __name__ == "__main__":
    main()
