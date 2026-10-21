from datetime import UTC, datetime
from io import BytesIO

import pyarrow as pa
import pyarrow.parquet as pa_parquet
import pytest

from etlrelay.core import Batch, Writer
from etlrelay.core.writer import WriterError
from etlrelay.writers import ParquetWriter


class TestParquetWriter:
    def test_writer_satisfies_protocol(self):
        writer = ParquetWriter()

        assert isinstance(writer, Writer)

    def test_writer_serializes_multiple_batches_to_parquet(self):
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
        stream = BytesIO()

        writer = ParquetWriter()
        writer.write(batches, stream)

        result = pa_parquet.read_table(BytesIO(stream.getvalue()))

        assert result.to_pylist() == [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]

    def test_writer_preserves_schema_and_arrow_types(self):
        schema = pa.schema(
            [
                pa.field("id", pa.int32()),
                pa.field("name", pa.string()),
                pa.field("score", pa.float64()),
                pa.field("active", pa.bool_()),
                pa.field(
                    "created_at",
                    pa.timestamp("us", tz="UTC"),
                ),
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
        stream = BytesIO()

        writer = ParquetWriter()
        writer.write(iter([Batch(table=table)]), stream)

        result = pa_parquet.read_table(BytesIO(stream.getvalue()))

        assert result.schema == schema
        assert result.equals(table)

    def test_writer_preserves_null_values(self):
        table = pa.table(
            {
                "id": pa.array(
                    [1, None, 3],
                    type=pa.int64(),
                ),
                "name": pa.array(
                    ["Alice", "Bob", None],
                    type=pa.string(),
                ),
            }
        )
        stream = BytesIO()

        writer = ParquetWriter()
        writer.write(iter([Batch(table=table)]), stream)

        result = pa_parquet.read_table(BytesIO(stream.getvalue()))

        assert result.to_pylist() == [
            {"id": 1, "name": "Alice"},
            {"id": None, "name": "Bob"},
            {"id": 3, "name": None},
        ]

    def test_writer_handles_empty_batch_with_schema(self):
        table = pa.table(
            {
                "name": pa.array([], type=pa.string()),
                "age": pa.array([], type=pa.int32()),
            }
        )
        stream = BytesIO()

        writer = ParquetWriter()
        writer.write(iter([Batch(table=table)]), stream)

        result = pa_parquet.read_table(BytesIO(stream.getvalue()))

        assert result.num_rows == 0
        assert result.schema == table.schema

    def test_writer_raises_error_for_empty_batch_iterable(self):
        stream = BytesIO()

        writer = ParquetWriter()

        with pytest.raises(WriterError):
            writer.write(iter([]), stream)

        assert stream.getvalue() == b""

    def test_writer_raises_error_for_incompatible_batch_schemas(self):
        batches = iter(
            [
                Batch(table=pa.table({"value": pa.array([1], type=pa.int64())})),
                Batch(table=pa.table({"value": pa.array(["two"], type=pa.string())})),
            ]
        )
        stream = BytesIO()

        writer = ParquetWriter()

        with pytest.raises(WriterError):
            writer.write(batches, stream)

    def test_writer_propagates_io_errors(self):
        class FailingStream(BytesIO):
            def write(self, data):
                raise OSError("Simulated write failure")

        table = pa.table({"id": [1, 2, 3]})
        stream = FailingStream()

        writer = ParquetWriter()

        with pytest.raises(OSError):
            writer.write(iter([Batch(table=table)]), stream)

    def test_writer_does_not_close_caller_owned_stream(self):
        table = pa.table({"id": [1, 2, 3]})
        stream = BytesIO()

        writer = ParquetWriter()
        writer.write(iter([Batch(table=table)]), stream)

        assert not stream.closed

def test_parquet_writer_accepts_metadata_only_schema_differences() -> None:
    """Accept batches whose schemas differ only in Arrow metadata."""
    first_schema = pa.schema(
        [
            pa.field(
                "id",
                pa.int64(),
                metadata={b"origin": b"first"},
            )
        ],
        metadata={b"version": b"1"},
    )

    second_schema = pa.schema(
        [
            pa.field(
                "id",
                pa.int64(),
                metadata={b"origin": b"second"},
            )
        ],
        metadata={b"version": b"2"},
    )

    first_batch = Batch(
        table=pa.Table.from_pylist(
            [{"id": 1}],
            schema=first_schema,
        )
    )

    second_batch = Batch(
        table=pa.Table.from_pylist(
            [{"id": 2}],
            schema=second_schema,
        )
    )

    stream = BytesIO()

    writer = ParquetWriter()
    writer.write([first_batch, second_batch], stream)

    result = pa_parquet.read_table(BytesIO(stream.getvalue()))

    assert result.column("id").to_pylist() == [1, 2]
    assert result.schema.equals(first_schema)