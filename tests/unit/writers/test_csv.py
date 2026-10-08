from io import BytesIO

import pyarrow as pa
import pytest

from flowforge.core.batch import Batch
from flowforge.core.writer import Writer, WriterError
from flowforge.writers.csv import CsvWriter


class TestCsvWriter:
    def test_writer_satisfies_protocol(self):
        writer = CsvWriter()

        assert isinstance(writer, Writer)

    def test_writer_serializes_batch_to_csv(self):
        batch = Batch(
            table=pa.table(
                {
                    "name": ["Alice", "Bob"],
                    "age": [30, 25],
                }
            )
        )
        stream = BytesIO()

        writer = CsvWriter()

        writer.write(batch, stream)

        csv_content = stream.getvalue().decode("utf-8")

        expected_csv_content = (
            '"name","age"\n'
            '"Alice",30\n'
            '"Bob",25\n'
        )

        assert csv_content == expected_csv_content

    def test_writer_raises_error_for_empty_batch(self):
        empty_batch = Batch(
            table=pa.table(
                {
                    "name": [],
                    "age": [],
                }
            )
        )
        stream = BytesIO()

        writer = CsvWriter()

        with pytest.raises(WriterError) as exc_info:
            writer.write(empty_batch, stream)

        assert str(exc_info.value) == (
            "Batch is empty. Cannot serialize an empty batch."
        )