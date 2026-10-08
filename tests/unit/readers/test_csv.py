
from pathlib import Path

import pytest

from flowforge.core.batch import Batch
from flowforge.readers.csv import CsvReader


class TestCsvReader:
    def test_reader_meets_protocol(self, tmp_path: Path):
        from flowforge.core.reader import Reader
        reader = CsvReader(tmp_path)
        assert isinstance(reader, Reader)

    def test_reader_can_read_valid_csv_file(self, tmp_path):
        # Create a temporary CSV file
        csv_content = "name,age\nAlice,30\nBob,25"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        # Read the CSV file using the reader
        reader = CsvReader(csv_file)
        data = reader.read()

        # Assert that the data read matches the expected output
        expected_data = Batch([
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"}
        ])
        assert data.table == expected_data.table
    
    def test_reader_handles_empty_csv_file(self, tmp_path):
        # Create an empty CSV file
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")

        # Read the empty CSV file using the reader
        reader = CsvReader(csv_file)
        data = reader.read()

        # Assert that the data read is an empty Batch
        expected_data = Batch([])
        assert data.table == expected_data.table
    
    def test_reader_raises_error_for_nonexistent_file(self):
        # Attempt to read a non-existent CSV file
        non_existent_file = Path("non_existent.csv")
        reader = CsvReader(non_existent_file)

        with pytest.raises(FileNotFoundError):
            reader.read()

    
    def test_csv_reader_raises_reader_error_for_invalid_encoding(
        self,
        tmp_path: Path,
    ):
        path = tmp_path / "invalid_encoding.csv"
        path.write_bytes(
            b"name,description\n"
            b"Alice,\xff\xfe\n"
        )

        reader = CsvReader(path)

        with pytest.raises(UnicodeDecodeError):
            reader.read()
    
