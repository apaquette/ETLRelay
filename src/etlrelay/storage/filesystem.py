"""Filesystem access contracts for ETLRelay.

This module defines the protocol for opening resources as binary streams
and the exception used to represent filesystem-related errors.

The interface separates storage access from file-format parsing and
serialization, allowing readers and writers to work independently of
the underlying storage implementation.
"""

from typing import BinaryIO, Protocol, runtime_checkable


class FileSystemError(Exception):
    """Represent a missing-input error in the filesystem contract.

    This exception is raised when an input resource does not exist. Other
    filesystem errors, including permission and I/O errors, should propagate
    as their original exceptions rather than being wrapped in FileSystemError.
    """


@runtime_checkable
class FileSystem(Protocol):
    """Define the interface for accessing file resources.

    Implementations provide readable and writable binary streams for
    storage resources. Callers are responsible for closing the returned
    streams, preferably by using a context manager.
    """

    def open_read(self, path: str) -> BinaryIO:
        """Open a resource for binary reading.

        The returned stream is owned by the caller, which is responsible for
        closing it.

        Args:
            path: Path or resource identifier understood by the implementation.

        Returns:
            A readable binary stream.

        Raises:
            FileSystemError: If the input resource does not exist.
            OSError: For other filesystem errors, including permission or I/O errors.
        """
        ...

    def open_write(self, path: str) -> BinaryIO:
        """Open a resource for binary writing.

        The returned stream is owned by the caller, which is responsible for
        closing it. The operation uses write-mode semantics rather than append
        semantics. For local files, an existing destination is truncated and a
        new destination is created if its parent directory exists. Parent
        directories are not created automatically.

        Args:
            path: Path or resource identifier understood by the implementation.

        Returns:
            A writable binary stream.

        Raises:
            OSError: If the destination cannot be opened for writing.
        """
        ...
