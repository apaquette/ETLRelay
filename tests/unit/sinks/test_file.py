from io import BytesIO
from unittest.mock import Mock

import pyarrow as pa
import pytest

from etlrelay.core.batch import Batch
from etlrelay.core.sink import Sink
from etlrelay.core.writer import Writer, WriterError
from etlrelay.sinks.file import FileSink
from etlrelay.storage.filesystem import FileSystem


class TestFileSink:
    def test_file_sink_satisfies_protocol(self):
        storage = Mock(spec=FileSystem)
        writer = Mock(spec=Writer)

        sink = FileSink(
            path="output.csv",
            storage=storage,
            writer=writer,
        )

        assert isinstance(sink, Sink)

    def test_file_sink_passes_batches_to_writer(self):
        stream = BytesIO()
        storage = Mock(spec=FileSystem)
        storage.open_write.return_value = stream

        writer = Mock(spec=Writer)
        received_batches = []

        def capture_write(batches, output_stream):
            received_batches.extend(batches)
            assert output_stream is stream

        writer.write.side_effect = capture_write

        batches = [
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

        sink = FileSink(
            path="output.csv",
            storage=storage,
            writer=writer,
        )

        sink.write(iter(batches))

        storage.open_write.assert_called_once_with("output.csv")
        writer.write.assert_called_once()
        assert received_batches == batches
        assert stream.closed

    def test_file_sink_handles_empty_iterable(self):
        stream = BytesIO()
        storage = Mock(spec=FileSystem)
        storage.open_write.return_value = stream

        writer = Mock(spec=Writer)
        received_batches = []

        writer.write.side_effect = lambda batches, output_stream: received_batches.extend(batches)

        sink = FileSink(
            path="output.csv",
            storage=storage,
            writer=writer,
        )

        sink.write(iter([]))

        writer.write.assert_called_once()
        assert received_batches == []
        assert stream.closed

    def test_file_sink_propagates_writer_error(self):
        stream = BytesIO()
        storage = Mock(spec=FileSystem)
        storage.open_write.return_value = stream

        writer = Mock(spec=Writer)
        writer.write.side_effect = WriterError("Serialization failed")

        sink = FileSink(
            path="output.csv",
            storage=storage,
            writer=writer,
        )

        batches = [Batch(table=pa.table({"name": ["Alice"]}))]

        with pytest.raises(WriterError, match="Serialization failed"):
            sink.write(iter(batches))

        assert stream.closed

    def test_file_sink_propagates_storage_error(self):
        storage = Mock(spec=FileSystem)
        storage.open_write.side_effect = OSError("Cannot open destination")

        writer = Mock(spec=Writer)

        sink = FileSink(
            path="output.csv",
            storage=storage,
            writer=writer,
        )

        with pytest.raises(OSError, match="Cannot open destination"):
            sink.write(iter([]))

        writer.write.assert_not_called()

    def test_file_sink_closes_stream_when_writer_fails(self):
        stream = BytesIO()
        storage = Mock(spec=FileSystem)
        storage.open_write.return_value = stream

        writer = Mock(spec=Writer)
        writer.write.side_effect = RuntimeError("Unexpected failure")

        sink = FileSink(
            path="output.csv",
            storage=storage,
            writer=writer,
        )

        with pytest.raises(RuntimeError, match="Unexpected failure"):
            sink.write(iter([]))

        assert stream.closed
