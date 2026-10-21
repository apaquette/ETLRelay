"""Source protocol for ETLRelay pipeline inputs.

This module defines the contract for components that provide batches of data
to a ETLRelay pipeline.
"""

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from etlrelay.core import Batch


@runtime_checkable
class Source(Protocol):
    """Define the interface for components that produce data batches.

    Sources expose batches through an iterable. Implementations determine
    how underlying resources are acquired and released.

    The Pipeline consumes the iterator returned by read() and explicitly
    closes it on termination if it provides a callable close() method.
    Source implementations that retain resources during iteration should
    support deterministic cleanup when iteration completes, fails, or
    is explicitly closed.
    """

    def read(self) -> Iterable[Batch]:
        """Return an iterable of batches obtained from the source.

        Resource acquisition may be lazy and occur during iteration rather
        than when this method is called.

        Direct consumers are responsible for closing active closeable
        iterators when they stop consumption early. Pipeline manages this
        cleanup when executing the source.

        Returns:
            An iterable producing Batch objects.

        Raises:
            Exception: Implementation-specific access, reading, or
                parsing failures propagate to the caller.
        """
        ...
