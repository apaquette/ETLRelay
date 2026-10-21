import logging
from collections.abc import Generator, Iterable
from io import BytesIO
from typing import BinaryIO, cast

import pyarrow as pa
import pytest

from etlrelay.core import Batch, Source
from etlrelay.sources import FileSource


class FakeFileSystem:
    """Provide a controlled binary stream for FileSource tests."""

    def __init__(
        self,
        stream: BinaryIO | None = None,
        error: Exception | None = None,
    ) -> None:
        self.stream = stream
        self.error = error
        self.opened_path: str | None = None

    def open_read(self, path: str) -> BinaryIO:
        self.opened_path = path

        if self.error is not None:
            raise self.error

        if self.stream is None:
            raise AssertionError("No stream configured for the test")

        return self.stream

    def open_write(self, path: str) -> BinaryIO:
        raise NotImplementedError("FileSource does not write files")


class FakeReader:
    """Yield a predefined Batch without parsing actual CSV data."""

    def __init__(
        self,
        batch: Batch,
        error: Exception | None = None,
    ) -> None:
        self.batch = batch
        self.error = error
        self.received_stream: BinaryIO | None = None

    def read(self, stream: BinaryIO) -> Iterable[Batch]:
        self.received_stream = stream

        if self.error is not None:
            raise self.error

        yield self.batch


class TestFileSource:
    @pytest.fixture
    def batch(self) -> Batch:
        return Batch(
            table=pa.table(
                {
                    "name": ["Alice", "Bob"],
                    "age": [30, 25],
                }
            )
        )

    def test_file_source_satisfies_source_protocol(
        self,
        batch: Batch,
    ) -> None:
        storage = FakeFileSystem(stream=BytesIO(b"test data"))
        reader = FakeReader(batch)

        source = FileSource(
            path="input.csv",
            storage=storage,
            reader=reader,
        )

        assert isinstance(source, Source)

    def test_file_source_reads_batch_using_storage_and_reader(
        self,
        batch: Batch,
    ) -> None:
        stream = BytesIO(b"name,age\nAlice,30\nBob,25")
        storage = FakeFileSystem(stream=stream)
        reader = FakeReader(batch)

        source = FileSource(
            path="input.csv",
            storage=storage,
            reader=reader,
        )

        result = list(source.read())

        assert len(result) == 1
        assert result[0] is batch
        assert storage.opened_path == "input.csv"
        assert reader.received_stream is stream

    def test_file_source_closes_stream_after_reading(
        self,
        batch: Batch,
    ) -> None:
        stream = BytesIO(b"name,age\nAlice,30")
        storage = FakeFileSystem(stream=stream)
        reader = FakeReader(batch)

        source = FileSource(
            path="input.csv",
            storage=storage,
            reader=reader,
        )

        list(source.read())

        assert stream.closed

    def test_file_source_propagates_storage_errors(
        self,
        batch: Batch,
    ) -> None:
        storage = FakeFileSystem(error=OSError("Unable to open file"))
        reader = FakeReader(batch)

        source = FileSource(
            path="input.csv",
            storage=storage,
            reader=reader,
        )

        with pytest.raises(OSError, match="Unable to open file"):
            list(source.read())

    def test_file_source_propagates_reader_errors(
        self,
        batch: Batch,
    ) -> None:
        stream = BytesIO(b"invalid CSV")
        storage = FakeFileSystem(stream=stream)
        reader = FakeReader(
            batch,
            error=ValueError("Unable to parse input"),
        )

        source = FileSource(
            path="input.csv",
            storage=storage,
            reader=reader,
        )

        with pytest.raises(ValueError, match="Unable to parse input"):
            list(source.read())

        assert stream.closed

    def test_file_source_passes_configured_path_to_storage(
        self,
        batch: Batch,
    ) -> None:
        stream = BytesIO(b"test data")
        storage = FakeFileSystem(stream=stream)
        reader = FakeReader(batch)

        source = FileSource(
            path="data/customers.csv",
            storage=storage,
            reader=reader,
        )

        list(source.read())

        assert storage.opened_path == "data/customers.csv"

    def test_file_source_closes_stream_when_iterator_is_closed_early(
        self,
        batch: Batch,
    ) -> None:
        stream = BytesIO(b"test data")
        storage = FakeFileSystem(stream=stream)

        class MultiBatchReader:
            def read(self, stream: BinaryIO) -> Iterable[Batch]:
                assert stream is stream
                yield batch
                yield batch

        source = FileSource(
            path="input.csv",
            storage=storage,
            reader=MultiBatchReader(),
        )

        iterator = cast(
            Generator[Batch, None, None],
            source.read(),
        )

        # FileSource.read() is lazy.
        assert not stream.closed

        assert next(iterator) is batch
        assert not stream.closed

        # Explicitly closing a partially consumed iterator must close the stream.
        iterator.close()

        assert stream.closed

    def test_read_logs_lifecycle_without_sensitive_values(
        self,
        batch: Batch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Log read lifecycle without exposing filenames or batch data."""
        sensitive_path = "private-customer-file.csv"

        storage = FakeFileSystem(stream=BytesIO(b"private-record-value"))
        reader = FakeReader(batch)

        source = FileSource(
            path=sensitive_path,
            storage=storage,
            reader=reader,
        )

        with caplog.at_level(logging.DEBUG, logger="etlrelay.sources.file"):
            batches = list(source.read())

        messages = [
            record.message for record in caplog.records if record.name == "etlrelay.sources.file"
        ]

        assert messages == [
            "File source read started.",
            "File source read completed.",
        ]

        assert sensitive_path not in caplog.text
        assert "private-record-value" not in caplog.text
        assert batches == [batch]
        assert storage.stream is not None
        assert storage.stream.closed

    def test_read_failure_does_not_log_completion(
        self,
        batch: Batch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Preserve the original failure without reporting successful completion."""
        error = RuntimeError("Failed to read private-record-value")

        storage = FakeFileSystem(stream=BytesIO(b"input"))
        reader = FakeReader(batch, error=error)

        source = FileSource(
            path="input.csv",
            storage=storage,
            reader=reader,
        )

        with caplog.at_level(logging.DEBUG, logger="etlrelay.sources.file"):
            iterator = source.read()

            # Constructing the iterator must not start file I/O or logging.
            assert caplog.records == []
            assert storage.opened_path is None

            with pytest.raises(RuntimeError) as exc_info:
                list(iterator)

        assert exc_info.value is error

        messages = [
            record.message for record in caplog.records if record.name == "etlrelay.sources.file"
        ]

        assert messages == ["File source read started."]
        assert "private-record-value" not in caplog.text
        assert storage.stream is not None
        assert storage.stream.closed


def test_file_source_closes_stream_when_reader_fails_after_first_batch(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Close the source stream when a reader fails after yielding data."""
    batch = Batch(table=pa.table({"id": [1]}))

    source_stream = BytesIO(b"input")
    storage = FakeFileSystem(stream=source_stream)

    failure = RuntimeError("Reader failed after first batch")

    class FailingReader:
        def read(self, stream: BinaryIO) -> Iterable[Batch]:
            assert stream is source_stream
            yield batch
            raise failure

    source = FileSource(
        path="input.csv",
        storage=storage,
        reader=FailingReader(),
    )

    iterator = iter(source.read())

    with caplog.at_level(
        logging.DEBUG,
        logger="etlrelay.sources.file",
    ):
        assert next(iterator) is batch
        assert not source_stream.closed

        with pytest.raises(RuntimeError) as exc_info:
            next(iterator)

    assert exc_info.value is failure
    assert source_stream.closed

    assert "File source read started." in caplog.text
    assert "File source read completed." not in caplog.text
