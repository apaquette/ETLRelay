"""File-based source implementation for ETLRelay.

This module provides a source that reads data from a file using a
filesystem abstraction and a reader implementation.
"""

from collections.abc import Iterable

from etlrelay.core import Batch, Reader
from etlrelay.storage import FileSystem


class FileSource:
    """Read data from a file and expose it as an iterable of batches.

    Attributes:
        path: The path to the file to read.
        storage: The filesystem used to open the file.
        reader: The reader used to parse the file contents into a batch.
    """

    path: str
    storage: FileSystem
    reader: Reader

    def __init__(self, path: str, storage: FileSystem, reader: Reader):
        """Initialize the file source.

        Args:
            path: The path to the file to read.
            storage: The filesystem used to access the file.
            reader: The reader used to parse the file contents.
        """
        self.path = path
        self.storage = storage
        self.reader = reader

    def read(self) -> Iterable[Batch]:
        """Yield batches parsed from the configured input file.

        File access and reading occur when the returned generator is consumed.
        The source opens the stream through the configured filesystem and passes
        it to the configured reader. The source manages the stream lifetime and
        closes it when iteration completes, reading raises an exception, or the
        generator is explicitly closed.

        Consumers that stop iteration early should explicitly close the generator
        when deterministic cleanup is required.

        Exceptions raised by the filesystem or reader propagate to the caller
        without being converted into format-independent errors.

        Returns:
            An iterable of batches parsed by the configured reader.
        """
        with self.storage.open_read(self.path) as stream:
            yield from self.reader.read(stream)
