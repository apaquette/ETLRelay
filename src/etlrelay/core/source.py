"""Source protocol for ETLRelay pipeline inputs.

This module defines the contract for components that provide batches of data
to a ETLRelay pipeline.
"""

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from etlrelay.core.batch import Batch


@runtime_checkable
class Source(Protocol):
    """Define the interface for components that produce data batches.

    Concrete source implementations are responsible for obtaining data from
    their respective data sources and exposing it as an iterable of Batch
    objects.

    The protocol is runtime-checkable, allowing implementations to be checked
    for protocol conformance using isinstance().
    """

    def read(self) -> Iterable[Batch]:
        """Return an iterable of batches obtained from the data source.

        Concrete implementations may raise implementation-specific
        exceptions when the underlying data cannot be accessed or read.

        Returns:
            An iterable of Batch objects produced by the source.
        """
        ...
