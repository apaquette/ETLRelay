"""File-based source implementation for ETLRelay.

This module provides a source that reads data from a file using a
filesystem abstraction and a reader implementation.
"""
from collections.abc import Iterable

from etlrelay.core.batch import Batch
from etlrelay.core.reader import Reader
from etlrelay.storage.filesystem import FileSystem


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
        """Read the file and return its data as an iterable of batches.

        Opens the file through the configured filesystem, parses its
        contents using the configured reader, and returns the resulting
        batch in an iterable.

        Returns:
            An iterable containing the batch parsed from the file.
        """
        with self.storage.open_read(self.path) as stream:
            yield from self.reader.read(stream)

    
