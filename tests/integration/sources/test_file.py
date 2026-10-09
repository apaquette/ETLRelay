from pathlib import Path

from etlrelay.readers import CsvReader
from etlrelay.security import PathValidator
from etlrelay.sources import FileSource
from etlrelay.storage import LocalFileSystem


class TestFileSource:
    def test_file_source_reads_csv_from_local_filesystem(
        self,
        tmp_path: Path,
    ):
        input_path = tmp_path / "input.csv"
        input_path.write_text(
            "name,age\nAlice,30\nBob,25\n",
            encoding="utf-8",
        )

        storage = LocalFileSystem(
            path_validator=PathValidator(base_path=tmp_path),
        )

        source = FileSource(
            path="input.csv",
            storage=storage,
            reader=CsvReader(),
        )

        batches = list(source.read())

        assert len(batches) == 1
        assert batches[0].table.column_names == ["name", "age"]
        assert batches[0].table.to_pylist() == [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
