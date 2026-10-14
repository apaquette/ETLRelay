from pathlib import Path

import pyarrow as pa

from etlrelay.core import Batch
from etlrelay.readers import CsvReader, ParquetReader
from etlrelay.security import PathValidator
from etlrelay.sinks import FileSink
from etlrelay.sources import FileSource
from etlrelay.storage import LocalFileSystem
from etlrelay.writers import CsvWriter, ParquetWriter


def make_local_storage(tmp_path: Path) -> LocalFileSystem:
    return LocalFileSystem(
        path_validator=PathValidator(base_path=tmp_path),
    )


class TestFileRoundTrip:
    def test_csv_file_sink_output_can_be_read_by_file_source(
        self,
        tmp_path: Path,
    ) -> None:
        table = pa.table(
            {
                "id": [1, 2, 3],
                "amount": [1.25, 2.5, 3.5],
            }
        )
        storage = make_local_storage(tmp_path)

        sink = FileSink(
            path="round_trip.csv",
            storage=storage,
            writer=CsvWriter(),
        )
        sink.write(iter([Batch(table=table)]))

        source = FileSource(
            path="round_trip.csv",
            storage=storage,
            reader=CsvReader(),
        )
        batches = list(source.read())

        assert batches
        result = pa.concat_tables([batch.table for batch in batches])

        assert result.to_pylist() == table.to_pylist()

    def test_parquet_file_sink_output_can_be_read_by_file_source(
        self,
        tmp_path: Path,
    ) -> None:
        table = pa.table(
            {
                "id": pa.array([1, None, 3], type=pa.int32()),
                "amount": pa.array(
                    [1.25, None, 3.5],
                    type=pa.float32(),
                ),
            }
        )
        storage = make_local_storage(tmp_path)

        sink = FileSink(
            path="round_trip.parquet",
            storage=storage,
            writer=ParquetWriter(),
        )
        sink.write(iter([Batch(table=table)]))

        source = FileSource(
            path="round_trip.parquet",
            storage=storage,
            reader=ParquetReader(),
        )
        batches = list(source.read())

        assert batches
        result = pa.concat_tables([batch.table for batch in batches])

        assert result.schema.equals(table.schema, check_metadata=False)
        assert result.to_pylist() == table.to_pylist()
