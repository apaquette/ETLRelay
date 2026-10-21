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
    """Define the interface for components that consume data batches.

    Concrete sinks deliver batches to their destinations and manage
    resources they acquire for the write operation.

    Persistence, transaction, overwrite, and empty-batch semantics are
    defined by each sink implementation rather than this protocol.
    """

    def write(self, batches: Iterable[Batch]) -> None:
        """Consume batches and write them to the destination.

        Implementations may consume batches lazily. They must release
        resources they own when writing completes or fails.

        A sink is not required to consume every batch before returning.
        The Pipeline manages cleanup of active source iterators when
        execution terminates.

        Args:
            batches: An iterable of batches to consume.

        Raises:
            Exception: Implementation-specific validation, serialization,
                storage, or database failures propagate to the caller.

        Note:
            Atomicity, rollback, overwrite behavior, and handling of
            empty batches depend on the concrete sink implementation.
        """
        ...
