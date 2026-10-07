
from typing import Protocol, runtime_checkable

from flowforge.core.batch import Batch


@runtime_checkable
class Processor(Protocol):
    def process(self, batch: Batch) -> Batch:
        ...