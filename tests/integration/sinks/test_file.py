from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from etlrelay.core import Batch
from etlrelay.security import PathValidator
from etlrelay.sinks import FileSink
from etlrelay.storage import LocalFileSystem
from etlrelay.writers import CsvWriter, ParquetWriter


def make_local_storage(tmp_path: Path) -> LocalFileSystem:
    return LocalFileSystem(
        path_validator=PathValidator(base_path=tmp_path),
    )


class TestFileSink:
    def test_file_sink_writes_multiple_batches_to_csv(
        self,
        tmp_path: Path,
    ):
        output_path = tmp_path / "output.csv"

        batches = iter(
            [
                Batch(
                    table=pa.table(
                        {
                            "name": ["Alice"],
                            "age": [30],
                        }
                    )
                ),
                Batch(
                    table=pa.table(
                        {
                            "name": ["Bob"],
                            "age": [25],
                        }
                    )
                ),
            ]
        )

        storage = make_local_storage(tmp_path)

        sink = FileSink(
            path="output.csv",
            storage=storage,
            writer=CsvWriter(),
        )

        sink.write(batches)

        assert output_path.is_file()
        assert output_path.read_text(encoding="utf-8") == ('"name","age"\n"Alice",30\n"Bob",25\n')

        def test_file_sink_writes_parquet_through_local_filesystem(
            self,
            tmp_path: Path,
        ) -> None:
            table = pa.table(
                {
                    "id": pa.array([1, 2, 3], type=pa.int32()),
                    "name": pa.array(["Alice", "Bob", "Cara"]),
                }
            )
            batches = [
                Batch(table=table.slice(0, 1)),
                Batch(table=table.slice(1, 2)),
            ]

            sink = FileSink(
                path="output.parquet",
                storage=make_local_storage(tmp_path),
                writer=ParquetWriter(),
            )

            sink.write(iter(batches))

            output_path = tmp_path / "output.parquet"
            assert output_path.is_file()

            result = pq.read_table(output_path)

            assert result.schema.equals(table.schema, check_metadata=False)
            assert result.to_pylist() == table.to_pylist()

    def test_file_sink_writes_parquet_through_local_filesystem(
        self,
        tmp_path: Path,
    ) -> None:
        table = pa.table(
            {
                "id": pa.array([1, 2, 3], type=pa.int32()),
                "name": pa.array(["Alice", "Bob", "Cara"]),
            }
        )
        batches = [
            Batch(table=table.slice(0, 1)),
            Batch(table=table.slice(1, 2)),
        ]

        sink = FileSink(
            path="output.parquet",
            storage=make_local_storage(tmp_path),
            writer=ParquetWriter(),
        )

        sink.write(iter(batches))

        output_path = tmp_path / "output.parquet"
        assert output_path.is_file()

        result = pq.read_table(output_path)

        assert result.schema.equals(table.schema, check_metadata=False)
        assert result.to_pylist() == table.to_pylist()

    def test_file_sink_writes_zero_row_batch_with_schema(
        self,
        tmp_path: Path,
    ) -> None:
        table = pa.table(
            {
                "id": pa.array([], type=pa.int32()),
                "name": pa.array([], type=pa.string()),
            }
        )

        sink = FileSink(
            path="empty.parquet",
            storage=make_local_storage(tmp_path),
            writer=ParquetWriter(),
        )

        sink.write(iter([Batch(table=table)]))

        result = pq.read_table(tmp_path / "empty.parquet")

        assert result.num_rows == 0
        assert result.schema.equals(table.schema, check_metadata=False)
