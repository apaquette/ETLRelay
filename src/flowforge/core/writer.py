
from typing import Protocol, runtime_checkable

from flowforge.core.batch import Batch


class WriterError(Exception):
    """Raised when a Writer fails to serialize or write data."""
    pass

@runtime_checkable
class Writer(Protocol):
    """Write a FlowForge Batch as serialized data."""
    def write(self, batch: Batch) -> None:
        """Serialize and write a batch to the given path.

        Raises:
            WriterError: If the batch cannot be serialized or written.
        """
        ...
