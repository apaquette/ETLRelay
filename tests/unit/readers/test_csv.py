from io import BytesIO

import pyarrow as pa
import pytest

from etlrelay.core import TabularReader
from etlrelay.readers import CsvReader


class TestCsvReader:
    def test_reader_meets_protocol(self):
        reader = CsvReader()

        assert isinstance(reader, TabularReader)

    def test_reader_can_read_valid_csv_data(self):
        csv_content = b"name,age\nAlice,30\nBob,25"
        stream = BytesIO(csv_content)

        reader = CsvReader()
        batches = list(reader.read(stream))

        rows = [row for batch in batches for row in batch.table.to_pylist()]

        assert rows == [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]

    def test_reader_handles_csv_with_header_and_no_rows(self):
        stream = BytesIO(b"name,age\n")

        reader = CsvReader()
        batches = list(reader.read(stream))

        assert batches == []

    def test_reader_raises_error_for_malformed_csv(self):
        stream = BytesIO(b"name,age\nAlice,30,extra\n")

        reader = CsvReader()

        with pytest.raises(pa.ArrowInvalid):
            list(reader.read(stream))


def test_csv_reader_does_not_close_caller_owned_stream() -> None:
    """Parsing CSV data must not close the supplied binary stream."""
    stream = BytesIO(b"id,name\n1,Alice\n")

    reader = CsvReader()
    batches = list(reader.read(stream))

    assert len(batches) == 1
    assert not stream.closed

    # The caller retains control over the stream.
    stream.seek(0)
    assert stream.read() == b"id,name\n1,Alice\n"

    stream.close()
    assert stream.closed


def test_csv_reader_preserves_stream_ownership_after_parse_failure() -> None:
    """A parsing failure does not transfer stream ownership to CsvReader."""
    stream = BytesIO(b"name,age\nAlice,30,unexpected\n")
    reader = CsvReader()

    with pytest.raises(pa.ArrowInvalid):
        list(reader.read(stream))

    assert not stream.closed

    stream.close()
