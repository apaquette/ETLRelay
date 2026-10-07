from typing import Protocol, runtime_checkable

from flowforge.core.batch import Batch


@runtime_checkable
class Sink(Protocol):
    def write(self, batch: Batch) -> None:
        ...