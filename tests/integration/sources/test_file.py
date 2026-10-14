from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from etlrelay.readers import CsvReader, ParquetReader
from etlrelay.security import PathValidator
from etlrelay.sources import FileSource
from etlrelay.storage import LocalFileSystem


def make_local_storage(tmp_path: Path) -> LocalFileSystem:
    return LocalFileSystem(
        path_validator=PathValidator(base_path=tmp_path),
    )


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

        storage = make_local_storage(tmp_path)

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

    def test_file_source_reads_parquet_from_local_filesystem(
        self,
        tmp_path: Path,
    ) -> None:
        table = pa.table(
            {
                "id": pa.array([1, 2, 3], type=pa.int32()),
                "name": pa.array(["Alice", "Bob", "Cara"]),
            }
        )
        pq.write_table(table, tmp_path / "input.parquet")

        source = FileSource(
            path="input.parquet",
            storage=make_local_storage(tmp_path),
            reader=ParquetReader(),
        )

        batches = list(source.read())

        assert batches
        result = pa.concat_tables([batch.table for batch in batches])

        assert result.schema.equals(table.schema, check_metadata=False)
        assert result.to_pylist() == table.to_pylist()

    def test_file_source_preserves_zero_row_parquet_schema(
        self,
        tmp_path: Path,
    ) -> None:
        table = pa.table(
            {
                "id": pa.array([], type=pa.int32()),
                "name": pa.array([], type=pa.string()),
            }
        )
        pq.write_table(table, tmp_path / "empty.parquet")

        source = FileSource(
            path="empty.parquet",
            storage=make_local_storage(tmp_path),
            reader=ParquetReader(),
        )

        batches = list(source.read())

        assert len(batches) == 1
        assert batches[0].table.num_rows == 0
        assert batches[0].table.schema.equals(
            table.schema,
            check_metadata=False,
        )
