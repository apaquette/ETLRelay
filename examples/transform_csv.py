"""Transform a sample CSV using ETLRelay's built-in processors."""

from pathlib import Path

from etlrelay.pipeline import Pipeline
from etlrelay.processors import FilterRows, RenameColumns, SelectColumns
from etlrelay.readers import CsvReader
from etlrelay.security import PathValidator
from etlrelay.sinks import FileSink
from etlrelay.sources import FileSource
from etlrelay.storage import LocalFileSystem
from etlrelay.writers import CsvWriter


def main() -> None:
    data_dir = Path(__file__).resolve().parent / "data"
    input_path = data_dir / "input.csv"

    if not input_path.is_file():
        raise FileNotFoundError(f"Example input CSV not found: {input_path}")

    storage = LocalFileSystem(
        path_validator=PathValidator(base_path=data_dir),
    )

    source = FileSource(
        path="input.csv",
        storage=storage,
        reader=CsvReader(),
    )
    sink = FileSink(
        path="transformed.csv",
        storage=storage,
        writer=CsvWriter(),
    )

    processors = [
        SelectColumns(columns=["name", "age"]),
        RenameColumns(mapping={"name": "customer_name"}),
        FilterRows(column="age", operator=">=", value=18),
    ]

    Pipeline(source=source, processors=processors, sink=sink).run()


if __name__ == "__main__":
    main()