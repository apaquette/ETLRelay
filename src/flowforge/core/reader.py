
from pathlib import Path
from typing import Protocol, runtime_checkable

from flowforge.core.batch import Batch


@runtime_checkable
class Reader(Protocol):
    """Read serialized data into a FlowForge Batch."""
    def read(self, path: Path) -> Batch:
        """Read and deserialize data from the given path.

        Raises:
            ReaderError: If the input data cannot be read or parsed.
        """
        ...