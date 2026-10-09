"""Protocols and exceptions for reading serialized data into ETLRelay batches."""

from collections.abc import Iterable
from typing import BinaryIO, Protocol, runtime_checkable

from etlrelay.core.batch import Batch


class ReaderError(Exception):
    """Raised when a reader fails to read or parse input data."""


@runtime_checkable
class Reader(Protocol):
    """Protocol for deserializing binary streams into ETLRelay batches.

    Implementations handle format-specific parsing independently of the
    storage system that provides the stream.
    """

    def read(self, stream: BinaryIO) -> Iterable[Batch]:
        """Read and deserialize data from a binary stream.

        Args:
            stream: An open binary stream containing serialized input data.

        Returns:
            An iterable of batches containing the parsed data.

        Raises:
            ReaderError: If the input data cannot be read or parsed.

        Note:
            The caller is responsible for managing the stream's lifecycle.
        """
        ...