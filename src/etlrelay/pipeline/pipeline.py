"""Pipeline orchestration for ETLRelay.

This module provides the Pipeline class, which coordinates batch processing
by passing data from a source through an ordered sequence of processors
and delivering the results to a sink.
"""

from collections.abc import Iterable, Sequence

from etlrelay.core.batch import Batch
from etlrelay.core.processor import Processor
from etlrelay.core.sink import Sink
from etlrelay.core.source import Source


class Pipeline:
    """Coordinate batch processing between a source, processors, and a sink.

    The pipeline obtains batches from a source, applies each configured
    processor in sequence, and passes the resulting batches to the sink.

    An empty processor sequence allows batches to pass through unchanged.
    Processing is synchronous, and exceptions from the source, processors,
    or sink propagate to the caller.
    """

    source: Source
    processors: Sequence[Processor]
    sink: Sink

    def __init__(
        self,
        source: Source,
        processors: Sequence[Processor],
        sink: Sink,
    ) -> None:
        """Initialize the pipeline with its source, processors, and sink.

        Args:
            source: Component that produces batches for processing.
            processors: Ordered sequence of processors to apply to each batch.
                May be empty if no transformations are required.
            sink: Component that consumes the processed batches.
        """
        self.source = source
        self.processors = processors
        self.sink = sink

    def run(self) -> None:
        """Execute the pipeline and deliver processed batches to the sink.

        Batches are obtained from the source, processed in sequence, and
        passed to the sink as an iterable. Processing is lazy, avoiding
        buffering all batches in memory before writing.

        Raises:
            Exception: Exceptions raised during source iteration, processing,
                or sink execution propagate to the caller.
        """
        batches = self._process_batches(self.source.read())
        self.sink.write(batches)

    def _process_batches(self, batches: Iterable[Batch]) -> Iterable[Batch]:
        """Process batches sequentially and yield the resulting batches.

        Each batch passes through every configured processor in order.
        The final result for each batch is yielded without collecting all
        results in memory.

        Args:
            batches: Iterable of batches to process.

        Yields:
            Each batch after all configured processors have been applied.
            If no processors are configured, each original batch is yielded
            unchanged.

        Raises:
            Exception: Exceptions raised by a processor or the input iterable
                propagate to the caller.
        """
        for batch in batches:
            for processor in self.processors:
                batch = processor.process(batch)
            yield batch