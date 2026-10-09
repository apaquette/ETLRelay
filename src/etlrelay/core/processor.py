"""Protocol for batch processing components in ETLRelay.

This module defines the interface that concrete processors must implement
to transform ETLRelay Batch objects.
"""

from typing import Protocol, runtime_checkable

from etlrelay.core.batch import Batch


@runtime_checkable
class Processor(Protocol):
    """Define the interface for ETLRelay batch processors.

    A processor accepts a Batch, applies a transformation, and returns
    the resulting Batch. Processors are executed sequentially by the
    pipeline.

    The protocol allows different processor implementations to be used
    interchangeably without coupling the pipeline to concrete classes.
    """

    def process(self, batch: Batch) -> Batch:
        """Transform a batch and return the resulting batch.

        Args:
            batch: The input Batch to process.

        Returns:
            The resulting Batch after applying the transformation.
        """
        ...
