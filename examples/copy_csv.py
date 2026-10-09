"""Copy a local CSV file through an ETLRelay pipeline."""

from pathlib import Path

from etlrelay.pipeline.pipeline import Pipeline
from etlrelay.readers.csv import CsvReader
from etlrelay.security.path import PathValidator
from etlrelay.sinks.file import FileSink
from etlrelay.sources.file import FileSource
from etlrelay.storage.local import LocalFileSystem
from etlrelay.writers.csv import CsvWriter


def main() -> None:
    data_dir = Path("data").resolve()
    storage = LocalFileSystem(
        path_validator=PathValidator(base_path=data_dir),
    )

    source = FileSource(
        path="input.csv",
        storage=storage,
        reader=CsvReader(),
    )
    sink = FileSink(
        path="output.csv",
        storage=storage,
        writer=CsvWriter(),
    )

    Pipeline(source=source, processors=[], sink=sink).run()


if __name__ == "__main__":
    main()
