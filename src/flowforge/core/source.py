
from typing import Protocol, runtime_checkable

from flowforge.core.batch import Batch


@runtime_checkable
class Source(Protocol):
    def read(self) -> Batch:
        ...