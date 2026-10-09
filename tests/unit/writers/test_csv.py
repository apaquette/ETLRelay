from io import BytesIO

import pyarrow as pa

from etlrelay.core.batch import Batch
from etlrelay.core.writer import Writer
from etlrelay.writers.csv import CsvWriter


class TestCsvWriter:
    def test_writer_satisfies_protocol(self):
        writer = CsvWriter()

        assert isinstance(writer, Writer)

    def test_writer_serializes_multiple_batches_to_csv(self):
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

        writer = CsvWriter()

        writer.write(batches, stream)

        csv_content = stream.getvalue().decode("utf-8")

        expected_csv_content = (
            '"name","age"\n'
            '"Alice",30\n'
            '"Bob",25\n'
        )

        assert csv_content == expected_csv_content

    def test_writer_handles_empty_batch(self):
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
        writer.write(iter([empty_batch]), stream)

        assert stream.getvalue().decode("utf-8") == '"name","age"\n'
    
    def test_writer_handles_empty_iterable(self):
        stream = BytesIO()

        writer = CsvWriter()
        writer.write(iter([]), stream)

        assert stream.getvalue() == b""