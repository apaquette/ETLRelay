
from collections.abc import Iterable
from typing import BinaryIO, Protocol, runtime_checkable

from flowforge.core.batch import Batch


class ReaderError(Exception):
    """Raised when a Reader fails to read or parse input data."""
    pass

@runtime_checkable
class Reader(Protocol):
    """Read serialized data into a FlowForge Batch."""
    def read(self, stream: BinaryIO) -> Iterable[Batch]:
        """Read and deserialize data from the given path.

        Raises:
            ReaderError: If the input data cannot be read or parsed.
        """
        ...