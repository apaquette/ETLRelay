"""File sink implementation for ETLRelay.

This module provides functionality for writing ETLRelay batches to a file
resource by combining a storage implementation with a format-specific
writer.
"""

from collections.abc import Iterable

from etlrelay.core import Batch, Writer
from etlrelay.storage import FileSystem


class FileSink:
    """Write batches to a file resource using a storage backend and writer.

    FileSink obtains a writable binary stream from the supplied FileSystem
    and passes the batches to the supplied Writer for serialization. It is
    independent of the underlying storage implementation and file format.

    Args:
        path: Path identifying the output resource.
        storage: Storage implementation used to open the output stream.
        writer: Writer used to serialize the batches.
    """

    path: str
    storage: FileSystem
    writer: Writer

    def __init__(self, path: str, storage: FileSystem, writer: Writer):
        """Initialize the file sink with its destination and dependencies.

        Args:
            path: Path identifying the output resource.
            storage: Storage implementation used to access the resource.
            writer: Writer used to serialize batches.
        """
        self.path = path
        self.storage = storage
        self.writer = writer

    def write(self, batches: Iterable[Batch]) -> None:
        """Serialize batches and write them to the configured destination.

        Opens the destination through the storage implementation and passes
        the resulting binary stream and batches to the writer. The stream is
        closed when writing completes or an exception occurs.

        Args:
            batches: Iterable of batches to serialize.

        Raises:
            OSError: If the storage implementation cannot open or write to
                the destination.
            Exception: Any exception raised by the writer is propagated.
        """
        with self.storage.open_write(self.path) as stream:
            self.writer.write(batches, stream)
