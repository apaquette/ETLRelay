from io import BytesIO

import pyarrow as pa
import pytest

from flowforge.core.reader import Reader
from flowforge.readers.csv import CsvReader


class TestCsvReader:
    def test_reader_meets_protocol(self):
        reader = CsvReader()

        assert isinstance(reader, Reader)

    def test_reader_can_read_valid_csv_data(self):
        csv_content = b"name,age\nAlice,30\nBob,25"
        stream = BytesIO(csv_content)

        reader = CsvReader()
        data = reader.read(stream)

        assert data.table.to_pylist() == [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]

    def test_reader_handles_csv_with_header_and_no_rows(self):
        stream = BytesIO(b"name,age\n")

        reader = CsvReader()
        data = reader.read(stream)

        assert data.table.num_rows == 0
        assert data.table.column_names == ["name", "age"]

    def test_reader_raises_error_for_malformed_csv(self):
        stream = BytesIO(
            b"name,age\n"
            b"Alice,30,extra\n"
        )

        reader = CsvReader()

        with pytest.raises(pa.ArrowInvalid):
            reader.read(stream)