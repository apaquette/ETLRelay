from datetime import UTC, datetime
from io import BytesIO

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from etlrelay.core import Reader
from etlrelay.readers import ParquetReader


def parquet_stream(table: pa.Table) -> BytesIO:
    """Serialize a PyArrow table into an in-memory Parquet stream."""
    stream = BytesIO()
    pq.write_table(table, stream)
    stream.seek(0)
    return stream


class TestParquetReader:
    def test_reader_meets_protocol(self):
        reader = ParquetReader()

        assert isinstance(reader, Reader)

    def test_reader_can_read_valid_parquet_data(self):
        table = pa.table(
            {
                "name": ["Alice", "Bob"],
                "age": [30, 25],
            }
        )
        stream = parquet_stream(table)

        reader = ParquetReader()
        batches = list(reader.read(stream))

        rows = [row for batch in batches for row in batch.table.to_pylist()]

        assert rows == [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]

    def test_reader_preserves_schema_and_arrow_types(self):
        schema = pa.schema(
            [
                pa.field("id", pa.int32()),
                pa.field("name", pa.string()),
                pa.field("score", pa.float64()),
                pa.field("active", pa.bool_()),
                pa.field("created_at", pa.timestamp("us", tz="UTC")),
            ]
        )
        table = pa.Table.from_arrays(
            [
                pa.array([1, 2], type=pa.int32()),
                pa.array(["Alice", "Bob"], type=pa.string()),
                pa.array([95.5, 87.0], type=pa.float64()),
                pa.array([True, False], type=pa.bool_()),
                pa.array(
                    [
                        datetime(2026, 1, 1, tzinfo=UTC),
                        datetime(2026, 1, 2, tzinfo=UTC),
                    ],
                    type=pa.timestamp("us", tz="UTC"),
                ),
            ],
            schema=schema,
        )
        stream = parquet_stream(table)

        reader = ParquetReader()
        batches = list(reader.read(stream))

        assert batches
        for batch in batches:
            assert batch.table.schema == schema

        result = pa.concat_tables([batch.table for batch in batches])
        assert result.equals(table)

    def test_reader_preserves_null_values(self):
        table = pa.table(
            {
                "id": pa.array([1, None, 3], type=pa.int64()),
                "name": pa.array(
                    ["Alice", "Bob", None],
                    type=pa.string(),
                ),
            }
        )
        stream = parquet_stream(table)

        reader = ParquetReader()
        batches = list(reader.read(stream))

        rows = [row for batch in batches for row in batch.table.to_pylist()]

        assert rows == [
            {"id": 1, "name": "Alice"},
            {"id": None, "name": "Bob"},
            {"id": 3, "name": None},
        ]

    def test_reader_preserves_schema_for_zero_row_parquet_file(self):
        schema = pa.schema(
            [
                pa.field("id", pa.int32()),
                pa.field("name", pa.string()),
            ]
        )
        table = pa.Table.from_batches([], schema=schema)
        stream = parquet_stream(table)

        reader = ParquetReader()
        batches = list(reader.read(stream))

        assert len(batches) == 1
        assert batches[0].table.num_rows == 0
        assert batches[0].table.schema == schema

    def test_reader_raises_reader_error_for_malformed_parquet(self):
        stream = BytesIO(b"this is not a valid Parquet file")

        reader = ParquetReader()

        with pytest.raises(pa.ArrowInvalid):
            list(reader.read(stream))

    def test_reader_does_not_close_caller_owned_stream(self):
        table = pa.table({"id": [1, 2, 3]})
        stream = parquet_stream(table)

        reader = ParquetReader()
        list(reader.read(stream))

        assert not stream.closed
