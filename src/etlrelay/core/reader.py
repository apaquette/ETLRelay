"""Protocols and exceptions for reading serialized data into ETLRelay batches."""

from collections.abc import Iterable, Mapping
from typing import Any, BinaryIO, Protocol, runtime_checkable

from etlrelay.core import Batch


class ReaderError(Exception):
    """Represent a read or parsing error normalized by a reader implementation."""


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

        Note:
            The caller retains ownership of the stream and is responsible for
            managing its lifecycle. Implementations may propagate format-specific
            parsing and I/O exceptions; the protocol does not normalize them into
            ReaderError.
        """
        ...


@runtime_checkable
class KeyValueReader(Protocol):
    def read(self, stream: BinaryIO) -> Mapping[str, Any]: ...
