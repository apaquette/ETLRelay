import logging
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from unittest.mock import Mock

import pyarrow as pa
import pytest

from etlrelay.core import Batch, Sink, TabularWriter, WriterError
from etlrelay.security import PathValidator
from etlrelay.sinks import FileSink
from etlrelay.storage import FileSystem, LocalFileSystem


class TestFileSink:
    def test_file_sink_satisfies_protocol(self):
        storage = Mock(spec=FileSystem)
        writer = Mock(spec=TabularWriter)

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

        writer = Mock(spec=TabularWriter)
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

        writer = Mock(spec=TabularWriter)
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

        writer = Mock(spec=TabularWriter)
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

        writer = Mock(spec=TabularWriter)

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

        writer = Mock(spec=TabularWriter)
        writer.write.side_effect = RuntimeError("Unexpected failure")

        sink = FileSink(
            path="output.csv",
            storage=storage,
            writer=writer,
        )

        with pytest.raises(RuntimeError, match="Unexpected failure"):
            sink.write(iter([]))

        assert stream.closed

    def test_file_sink_closes_stream_and_leaves_partial_output_when_writer_fails(
        self,
        tmp_path: Path,
    ):
        output_path = tmp_path / "output.bin"
        output_path.write_bytes(b"original content")

        storage = LocalFileSystem(path_validator=PathValidator(base_path=tmp_path))

        writer = Mock(spec=TabularWriter)
        opened_streams: list[BinaryIO] = []

        def write_partial_then_fail(
            _batches: Iterable[Batch],
            output_stream: BinaryIO,
        ) -> None:
            opened_streams.append(output_stream)
            output_stream.write(b"partial")
            raise WriterError("Serialization failed")

        writer.write.side_effect = write_partial_then_fail

        sink = FileSink(
            path="output.bin",
            storage=storage,
            writer=writer,
        )

        with pytest.raises(WriterError, match="Serialization failed"):
            sink.write(iter([]))

        assert len(opened_streams) == 1
        assert opened_streams[0].closed

        # Opening with "wb" truncates the old file before writing starts.
        # A failed write does not restore the original contents.
        assert output_path.read_bytes() == b"partial"

    def test_write_logs_lifecycle_without_sensitive_values(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Log output lifecycle without exposing filenames or record values."""
        sensitive_path = "private-output.csv"

        stream = BytesIO()
        storage = Mock(spec=FileSystem)
        storage.open_write.return_value = stream

        writer = Mock(spec=TabularWriter)
        sink = FileSink(
            path=sensitive_path,
            storage=storage,
            writer=writer,
        )

        batches = [Batch(table=pa.table({"name": ["private-customer-value"]}))]

        with caplog.at_level(logging.DEBUG, logger="etlrelay.sinks.file"):
            sink.write(batches)

        messages = [
            record.message for record in caplog.records if record.name == "etlrelay.sinks.file"
        ]

        assert messages == [
            "File sink write started.",
            "File sink write completed.",
        ]

        assert sensitive_path not in caplog.text
        assert "private-customer-value" not in caplog.text
        assert stream.closed

        storage.open_write.assert_called_once_with(sensitive_path)
        writer.write.assert_called_once()

    def test_write_failure_preserves_exception_without_logging_payload(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Preserve the writer exception and omit its sensitive message."""
        error = WriterError("Serialization failed for private-record-value")

        stream = BytesIO()
        storage = Mock(spec=FileSystem)
        storage.open_write.return_value = stream

        writer = Mock(spec=TabularWriter)
        writer.write.side_effect = error

        sink = FileSink(
            path="output.csv",
            storage=storage,
            writer=writer,
        )

        with caplog.at_level(logging.DEBUG, logger="etlrelay.sinks.file"):
            with pytest.raises(WriterError) as exc_info:
                sink.write([])

        assert exc_info.value is error

        messages = [
            record.message for record in caplog.records if record.name == "etlrelay.sinks.file"
        ]

        assert messages == ["File sink write started."]
        assert "private-record-value" not in caplog.text
        assert stream.closed


def test_file_sink_leaves_empty_output_when_writer_fails_before_writing(
    tmp_path: Path,
) -> None:
    """An existing output is truncated even if serialization never starts."""
    output_path = tmp_path / "output.bin"
    output_path.write_bytes(b"original content")

    storage = LocalFileSystem(
        path_validator=PathValidator(base_path=tmp_path),
    )

    failure = WriterError("Serialization failed before writing")

    writer = Mock(spec=TabularWriter)
    writer.write.side_effect = failure

    sink = FileSink(
        path="output.bin",
        storage=storage,
        writer=writer,
    )

    with pytest.raises(WriterError) as exc_info:
        sink.write(iter([]))

    assert exc_info.value is failure

    # Opening the destination in "wb" mode truncates it immediately.
    # The failed writer cannot restore the original contents.
    assert output_path.exists()
    assert output_path.read_bytes() == b""

    writer.write.assert_called_once()
