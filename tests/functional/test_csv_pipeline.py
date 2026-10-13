from pathlib import Path

from etlrelay.pipeline import Pipeline
from etlrelay.readers import CsvReader
from etlrelay.security import PathValidator
from etlrelay.sinks import FileSink
from etlrelay.sources import FileSource
from etlrelay.storage import LocalFileSystem
from etlrelay.writers import CsvWriter
from etlrelay.processors import FilterRows, RenameColumns, SelectColumns

from collections.abc import Iterable

import pyarrow as pa

from etlrelay.core import Batch

class FixedBatchSource:
    def __init__(self, batches: list[Batch]):
        self._batches = batches

    def read(self) -> Iterable[Batch]:
        return iter(self._batches)


def test_csv_pipeline_transfers_data_between_files(
    tmp_path: Path,
):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"

    input_path.write_text(
        "name,age\nAlice,30\nBob,25\n",
        encoding="utf-8",
    )

    storage = LocalFileSystem(
        path_validator=PathValidator(base_path=tmp_path),
    )

    pipeline = Pipeline(
        source=FileSource(
            path="input.csv",
            storage=storage,
            reader=CsvReader(),
        ),
        processors=[],
        sink=FileSink(
            path="output.csv",
            storage=storage,
            writer=CsvWriter(),
        ),
    )

    pipeline.run()

    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == ('"name","age"\n"Alice",30\n"Bob",25\n')

def test_csv_pipeline_applies_column_transformations(
    tmp_path: Path,
):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"

    input_path.write_text(
        "name,age,department\n"
        "Alice,17,Engineering\n"
        "Bob,25,Data\n"
        "Charlie,18,QA\n"
        "Diana,16,Data\n"
        "Evan,42,Engineering\n",
        encoding="utf-8",
    )

    storage = LocalFileSystem(
        path_validator=PathValidator(base_path=tmp_path),
    )

    pipeline = Pipeline(
        source=FileSource(
            path="input.csv",
            storage=storage,
            reader=CsvReader(),
        ),
        processors=[
            SelectColumns(columns=["name", "age"]),
            RenameColumns(mapping={"name": "customer_name"}),
            FilterRows(column="age", operator=">=", value=18),
        ],
        sink=FileSink(
            path="output.csv",
            storage=storage,
            writer=CsvWriter(),
        ),
    )

    pipeline.run()

    assert output_path.is_file()
    assert output_path.read_text(encoding="utf-8") == (
        '"customer_name","age"\n'
        '"Bob",25\n'
        '"Charlie",18\n'
        '"Evan",42\n'
    )

def test_csv_pipeline_writes_header_for_zero_row_batch(
    tmp_path: Path,
):
    output_path = tmp_path / "output.csv"

    schema = pa.schema(
        [
            pa.field("name", pa.string(), nullable=False),
            pa.field("age", pa.int64(), nullable=False),
        ]
    )
    empty_batch = Batch(
        table=pa.Table.from_pylist([], schema=schema)
    )

    storage = LocalFileSystem(
        path_validator=PathValidator(base_path=tmp_path),
    )

    pipeline = Pipeline(
        source=FixedBatchSource([empty_batch]),
        processors=[],
        sink=FileSink(
            path="output.csv",
            storage=storage,
            writer=CsvWriter(),
        ),
    )

    pipeline.run()

    assert output_path.is_file()
    assert output_path.read_text(encoding="utf-8") == (
        '"name","age"\n'
    )