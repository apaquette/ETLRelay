from pathlib import Path

import pyarrow as pa

from etlrelay.core.batch import Batch
from etlrelay.security.path import PathValidator
from etlrelay.sinks.file import FileSink
from etlrelay.storage.local import LocalFileSystem
from etlrelay.writers.csv import CsvWriter


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

        storage = LocalFileSystem(
            path_validator=PathValidator(base_path=tmp_path),
        )

        sink = FileSink(
            path="output.csv",
            storage=storage,
            writer=CsvWriter(),
        )

        sink.write(batches)

        assert output_path.is_file()
        assert output_path.read_text(encoding="utf-8") == ('"name","age"\n"Alice",30\n"Bob",25\n')
