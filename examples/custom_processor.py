"""Use an application-defined processor without changing the built-in catalog."""

from pathlib import Path

import pyarrow.compute as pc

from etlrelay.core import Batch, Processor
from etlrelay.pipeline import Pipeline
from etlrelay.readers import CsvReader
from etlrelay.security import PathValidator
from etlrelay.sinks import FileSink
from etlrelay.sources import FileSource
from etlrelay.storage import LocalFileSystem
from etlrelay.writers import CsvWriter


class UppercaseNames:
    """Uppercase the name field while preserving its schema and null values."""

    def process(self, batch: Batch) -> Batch:
        table = batch.table
        index = table.schema.get_field_index("name")
        if index == -1:
            raise ValueError("Expected an unambiguous name column")
        return Batch(
            table.set_column(index, table.schema.field(index), pc.utf8_upper(table[index]))
        )


def main() -> None:
    data_dir = Path(__file__).resolve().parent / "data"
    storage = LocalFileSystem(PathValidator(data_dir))
    processor: Processor = UppercaseNames()
    Pipeline(
        FileSource("input.csv", storage, CsvReader()),
        [processor],
        FileSink("uppercase_output.csv", storage, CsvWriter()),
    ).run()


if __name__ == "__main__":
    main()
