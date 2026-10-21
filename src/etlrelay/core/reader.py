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
            The caller retains ownership of the supplied stream and must close
            it when appropriate. Reader implementations must not close the
            caller-owned stream, including when parsing fails.

            Concrete readers may have additional stream requirements, such
            as seekability for Parquet input.
        """
        ...


@runtime_checkable
class KeyValueReader(Protocol):
    def read(self, stream: BinaryIO) -> Mapping[str, Any]: ...
