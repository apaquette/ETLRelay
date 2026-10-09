from collections.abc import Iterable
from io import BytesIO
from typing import BinaryIO

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
