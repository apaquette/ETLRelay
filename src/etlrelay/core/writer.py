"""Protocols and exceptions for serializing ETLRelay batches."""

from collections.abc import Iterable
from typing import BinaryIO, Protocol, runtime_checkable

from etlrelay.core.batch import Batch


class WriterError(Exception):
    """Raised when a writer cannot serialize the supplied batches."""


@runtime_checkable
class Writer(Protocol):
    """Define the interface for serializing batches to a binary stream.

    Implementations are responsible for format-specific serialization.
    They do not manage filesystem access or the lifecycle of the supplied
    stream.
    """

    def write(self, batches: Iterable[Batch], stream: BinaryIO) -> None:
        """Serialize batches and write the resulting data to a stream.

        Args:
            batches: An iterable of batches to serialize into one output.
            stream: A writable binary stream that receives the serialized
                data. The caller is responsible for closing the stream.

        Raises:
            WriterError: If the batches cannot be serialized.
            OSError: If an I/O error occurs while writing to the stream.
        """
        ...