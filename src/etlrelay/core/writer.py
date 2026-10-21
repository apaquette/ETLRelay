"""Protocol and exception for serializing ETLRelay tabular batches."""

from collections.abc import Iterable
from typing import BinaryIO, Protocol, runtime_checkable

from etlrelay.core import Batch


class WriterError(Exception):
    """Represent a serialization failure normalized by a writer implementation."""


@runtime_checkable
class TabularWriter(Protocol):
    """Define the interface for writing tabular batches to a binary stream.

    Implementations perform format-specific serialization independently of
    filesystem access. The supplied stream remains owned by the caller.
    """

    def write(self, batches: Iterable[Batch], stream: BinaryIO) -> None:
        """Serialize batches into one output stream.

        Args:
            batches: An iterable of batches to serialize.
            stream: An open, writable binary stream receiving serialized data.

        Note:
            The caller owns the output stream. Implementations must not
            close it, including when serialization or batch iteration fails.

            The method consumes batches synchronously. It may leave partial
            output if serialization or iteration fails; this protocol does
            not provide atomic writes or rollback.

            Empty-input behavior, schema compatibility, stream requirements,
            and serialization errors are documented by each implementation.
        """
        ...
