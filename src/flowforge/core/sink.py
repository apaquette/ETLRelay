from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from flowforge.core.batch import Batch


@runtime_checkable
class Sink(Protocol):
    def write(self, batch: Iterable[Batch]) -> None:
        ...