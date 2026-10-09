from pathlib import Path

from etlrelay.pipeline import Pipeline
from etlrelay.readers import CsvReader
from etlrelay.security import PathValidator
from etlrelay.sinks import FileSink
from etlrelay.sources import FileSource
from etlrelay.storage import LocalFileSystem
from etlrelay.writers import CsvWriter


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
