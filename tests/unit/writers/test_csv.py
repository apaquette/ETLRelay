
from pathlib import Path

from flowforge.core.batch import Batch
from flowforge.core.writer import WriterError
from flowforge.writers.csv import CsvWriter


class TestCsvWriter:
    def test_writer_satisfies_protocol(self, tmp_path: Path):
        from flowforge.core.writer import Writer
        writer = CsvWriter(tmp_path)

        assert isinstance(writer, Writer), "CsvWriter should be an instance of CsvWriter class."

    def test_writer_serializes_batch_to_supplied_path_in_csv_format(self, tmp_path):
        # Create a temporary CSV file path
        csv_file_path = tmp_path / "output.csv"

        # Create a sample Batch object
        batch = Batch(table=[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}])

        # Create an instance of CsvWriter
        writer = CsvWriter(csv_file_path)

        # Call the write method to serialize the batch to CSV
        writer.write(batch)

        # Read the contents of the CSV file and verify its contents
        with open(csv_file_path, encoding="utf-8") as csv_file:
            csv_content = csv_file.read()

        expected_csv_content = "name,age\nAlice,30\nBob,25\n"
        assert csv_content == expected_csv_content, "CSV content does not match expected output."
    
    def test_writer_raises_error_for_empty_batch(self, tmp_path):
        # Create a temporary CSV file path
        csv_file_path = tmp_path / "output.csv"

        # Create an empty Batch object
        empty_batch = Batch(table=[])

        # Create an instance of CsvWriter
        writer = CsvWriter(csv_file_path)

        # Expect a WriterError to be raised when trying to write an empty batch
        import pytest
        with pytest.raises(WriterError) as exc_info:
            writer.write(empty_batch)

        assert str(exc_info.value) == "Batch is empty. Cannot serialize an empty batch."