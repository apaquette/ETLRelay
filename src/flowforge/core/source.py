
from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from flowforge.core.batch import Batch


@runtime_checkable
class Source(Protocol):
    def read(self) -> Iterable[Batch]:
        ...