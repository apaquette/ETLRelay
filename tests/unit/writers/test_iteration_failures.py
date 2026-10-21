"""Borrowed output streams and partial serialization after upstream failure."""

from collections.abc import Iterator
from io import BytesIO

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import pytest

from etlrelay.core import Batch, TabularWriter
from etlrelay.writers import CsvWriter, ParquetWriter


@pytest.mark.parametrize("file_format", ["csv", "parquet"])
def test_writer_preserves_iteration_error_and_leaves_stream_open(file_format: str) -> None:
    failure = RuntimeError("upstream batch failure")
    stream = BytesIO()
    writer: TabularWriter = CsvWriter() if file_format == "csv" else ParquetWriter()

    def batches() -> Iterator[Batch]:
        yield Batch(pa.table({"id": [1]}))
        raise failure

    with pytest.raises(RuntimeError) as caught:
        writer.write(batches(), stream)

    assert caught.value is failure
    assert not stream.closed
    stream.seek(0)
    # Finalization succeeded, so the prefix is readable despite pipeline failure.
    table = pacsv.read_csv(stream) if file_format == "csv" else pq.read_table(stream)
    assert table.to_pylist() == [{"id": 1}]
