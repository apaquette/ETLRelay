from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from etlrelay.pipeline import Pipeline
from etlrelay.processors import FilterRows, RenameColumns, SelectColumns
from etlrelay.readers import ParquetReader
from etlrelay.security import PathValidator
from etlrelay.sinks import FileSink
from etlrelay.sources import FileSource
from etlrelay.storage import LocalFileSystem
from etlrelay.writers import ParquetWriter


def make_local_storage(tmp_path: Path) -> LocalFileSystem:
    return LocalFileSystem(
        path_validator=PathValidator(base_path=tmp_path),
    )


def test_local_parquet_pipeline_transforms_and_writes_data(
    tmp_path: Path,
) -> None:
    input_table = pa.table(
        {
            "name": pa.array(["Alice", "Bob", "Cara"]),
            "age": pa.array([17, 30, 21], type=pa.int64()),
            "city": pa.array(["Halifax", "Dublin", "Moncton"]),
        }
    )
    pq.write_table(input_table, tmp_path / "input.parquet")

    storage = make_local_storage(tmp_path)

    source = FileSource(
        path="input.parquet",
        storage=storage,
        reader=ParquetReader(),
    )
    sink = FileSink(
        path="output.parquet",
        storage=storage,
        writer=ParquetWriter(),
    )
    processors = [
        SelectColumns(columns=["name", "age"]),
        RenameColumns(mapping={"name": "customer_name"}),
        FilterRows(column="age", operator=">=", value=18),
    ]

    pipeline = Pipeline(
        source=source,
        processors=processors,
        sink=sink,
    )
    pipeline.run()

    result = pq.read_table(tmp_path / "output.parquet")

    expected_schema = pa.schema(
        [
            pa.field("customer_name", pa.string()),
            pa.field("age", pa.int64()),
        ]
    )

    assert result.schema.equals(expected_schema, check_metadata=False)
    assert result.to_pylist() == [
        {"customer_name": "Bob", "age": 30},
        {"customer_name": "Cara", "age": 21},
    ]
