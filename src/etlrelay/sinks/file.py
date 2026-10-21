"""File sink implementation for ETLRelay.

This module provides functionality for writing ETLRelay batches to a file
resource by combining a storage implementation with a format-specific
writer.
"""

import logging
from collections.abc import Iterable

from etlrelay.core import Batch, TabularWriter
from etlrelay.storage import FileSystem

logger = logging.getLogger(__name__)


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
    writer: TabularWriter

    def __init__(self, path: str, storage: FileSystem, writer: TabularWriter):
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
        Note:
            FileSink owns and closes the stream returned by FileSystem.open_write().
            It does not close or otherwise manage the supplied FileSystem or Writer
            instances.

            With LocalFileSystem, an existing destination is truncated when
            opened for writing. If serialization fails, an empty or partially
            written file may remain. Previous contents are not restored.

            File writes are not atomic and are not rolled back.
            Format-specific empty-input behavior is determined by the Writer.
        """
        logger.debug("File sink write started.")

        with self.storage.open_write(self.path) as stream:
            self.writer.write(batches, stream)

        logger.debug("File sink write completed.")
