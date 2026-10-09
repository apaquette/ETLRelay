"""Filesystem access contracts for ETLRelay.

This module defines the protocol for opening resources as binary streams
and the exception used to represent filesystem-related errors.

The interface separates storage access from file-format parsing and
serialization, allowing readers and writers to work independently of
the underlying storage implementation.
"""

from typing import BinaryIO, Protocol, runtime_checkable


class FileSystemError(Exception):
    """Raised when a filesystem operation fails."""


@runtime_checkable
class FileSystem(Protocol):
    """Define the interface for accessing file resources.

    Implementations provide readable and writable binary streams for
    storage resources. Callers are responsible for closing the returned
    streams, preferably by using a context manager.
    """

    def open_read(self, path: str) -> BinaryIO:
        """Open a resource for binary reading.

        Args:
            path: The path or resource identifier understood by the
                filesystem implementation.

        Returns:
            A readable binary stream.

        Raises:
            OSError: If the resource cannot be opened for reading.
        """
        ...

    def open_write(self, path: str) -> BinaryIO:
        """Open a resource for binary writing.

        Args:
            path: The path or resource identifier understood by the
                filesystem implementation.

        Returns:
            A writable binary stream.

        Raises:
            OSError: If the resource cannot be opened for writing.
        """
        ...
