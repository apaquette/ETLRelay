"""Sink protocol for consuming ETLRelay batches.

This module defines the interface that sink implementations use to receive
batches produced by a pipeline. Concrete sinks determine how and where the
batches are written.
"""

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from etlrelay.core import Batch


@runtime_checkable
class Sink(Protocol):
    """Define the interface for components that consume batches.

    Concrete implementations are responsible for delivering batches to
    their destination, such as a file or database. The protocol is
    independent of any particular storage backend or output format.
    """

    def write(self, batches: Iterable[Batch]) -> None:
        """Write an iterable of batches to the configured destination.

        Args:
            batches: An iterable of batches to consume and write.

        Raises:
            Exception: If writing fails. Concrete implementations may raise
                more specific exceptions for their respective failure cases.
        """
        ...
