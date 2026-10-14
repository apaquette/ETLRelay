"""Run a local Parquet pipeline using ETLRelay's public composition API.

Run from the repository root after installing the project:
    uv run python examples/parquet_pipeline.py
"""
from pathlib import Path

import pyarrow as pa

from etlrelay.core import Batch
from etlrelay.pipeline import Pipeline
from etlrelay.processors import FilterRows, RenameColumns, SelectColumns
from etlrelay.readers import ParquetReader
from etlrelay.security import PathValidator
from etlrelay.sinks import FileSink
from etlrelay.sources import FileSource
from etlrelay.storage import LocalFileSystem
from etlrelay.writers import ParquetWriter


def main() -> None:
    data_dir = Path("data").resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    storage = LocalFileSystem(
        path_validator=PathValidator(base_path=data_dir),
    )

    input_batch = Batch(
        table=pa.table(
            {
                "name": ["Alice", "Bob", "Charlie", "Diana", "Evan"],
                "age": [17, 25, 18, 16, 42],
                "department": [
                    "Engineering",
                    "Data",
                    "QA",
                    "Data",
                    "Engineering",
                ],
            }
        )
    )

    # Create the input file through the same public sink composition.
    FileSink(
        path="input.parquet",
        storage=storage,
        writer=ParquetWriter(),
    ).write([input_batch])

    pipeline = Pipeline(
        source=FileSource(
            path="input.parquet",
            storage=storage,
            reader=ParquetReader(),
        ),
        processors=[
            SelectColumns(columns=["name", "age"]),
            RenameColumns(mapping={"name": "customer_name"}),
            FilterRows(column="age", operator=">=", value=18),
        ],
        sink=FileSink(
            path="output.parquet",
            storage=storage,
            writer=ParquetWriter(),
        ),
    )
    pipeline.run()
    print(f"Wrote {data_dir / 'output.parquet'}")


if __name__ == "__main__":
    main()
