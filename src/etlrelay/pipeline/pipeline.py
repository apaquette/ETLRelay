"""Pipeline orchestration for ETLRelay.

This module provides the Pipeline class, which coordinates batch processing
by passing data from a source through an ordered sequence of processors
and delivering compatible output batches to a sink.
"""

import logging
from collections.abc import Iterable, Iterator, Sequence
from itertools import chain

import pyarrow as pa

from etlrelay.core import Batch, Processor, Sink, Source

logger = logging.getLogger(__name__)


class Pipeline:
    """Coordinate batch processing between a source, processors, and a sink.

    The pipeline obtains batches from a source, applies each configured
    processor in sequence, validates the resulting output schemas, and passes
    compatible batches to the sink.

    The first processed output batch establishes the expected schema for the
    run. Subsequent output batches must have matching field names, field order,
    Arrow types, and nullability. Schema metadata differences are ignored.
    Zero-row batches participate in schema validation.

    Processing is lazy and does not buffer all batches before writing. If a
    later batch has an incompatible schema, a ValueError is raised before that
    batch is yielded to the sink. Batches successfully written before a later
    failure are not rolled back.

    Exceptions from the source, processors, or sink otherwise propagate to
    the caller.

    Pipeline owns the consumption lifecycle of the source iterator for the
    duration of run(). When execution terminates, it attempts to close both
    the processing iterator and the underlying source iterator when they
    provide callable close() methods.

    This cleanup occurs after successful execution, early sink termination,
    or failures during source iteration, processing, or sink execution.

    Execution exceptions take precedence over iterator cleanup failures.
    Secondary cleanup failures are logged without their exception messages.
    If execution otherwise succeeds but cleanup fails, the first cleanup
    exception propagates.

    Pipeline does not own or dispose the underlying storage backends,
    database engines, or component instances.
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

        Batches are processed lazily and passed to the sink without buffering
        the entire input. If the source produces no batches, the sink is not
        called.

        Close active source and processing iterators when execution terminates,
        including when the sink stops consuming batches early.

        Exceptions from the source, processors, or sink propagate unchanged.
        If iterator cleanup also fails, the original execution exception takes
        precedence. Cleanup failures are logged without exposing their messages.
        """
        logger.info("Pipeline execution started.")

        source_batches = iter(self.source.read())
        batches = self._process_batches(source_batches)

        execution_failed = False

        try:
            try:
                first_batch = next(batches)
            except StopIteration:
                pass
            else:
                self.sink.write(chain((first_batch,), batches))

        except BaseException:
            execution_failed = True
            raise

        finally:
            cleanup_error: Exception | None = None

            for iterator in (batches, source_batches):
                close = getattr(iterator, "close", None)

                if not callable(close):
                    continue

                try:
                    close()
                except Exception as error:
                    logger.warning(
                        "Pipeline iterator cleanup failed (%s).",
                        type(error).__name__,
                    )

                    if cleanup_error is None:
                        cleanup_error = error

            if cleanup_error is not None and not execution_failed:
                raise cleanup_error

        logger.info("Pipeline execution completed.")

    def _process_batches(self, batches: Iterable[Batch]) -> Iterator[Batch]:
        """Process batches sequentially, validate their output schemas, and yield them.

        Each batch passes through every configured processor in order. The first
        processed output batch establishes the expected schema. Each subsequent
        processed output schema is checked for compatible field names, order,
        Arrow types, and nullability. Schema metadata differences are ignored.

        Validation occurs before a batch is yielded, and batches are yielded
        incrementally without collecting all results in memory. Zero-row batches
        are processed and validated like any other batch.

        Args:
            batches: Iterable of batches to process.

        Yields:
            Each batch after all configured processors have been applied and its
            output schema has been validated. If no processors are configured,
            the original batches are yielded when their schemas are compatible.

        Raises:
            ValueError: If a processed output schema differs from the expected
                schema for the run.
            Exception: Exceptions raised by a processor or the input iterable
                propagate to the caller.
        """
        expected_schema: pa.Schema | None = None
        for batch_number, batch in enumerate(batches, start=1):
            for processor in self.processors:
                batch = processor.process(batch)

            actual_schema = batch.table.schema

            if expected_schema is None:
                expected_schema = actual_schema
            elif not expected_schema.equals(actual_schema, check_metadata=False):
                raise ValueError(
                    f"Incompatible output schema: expected {expected_schema}, got {actual_schema}"
                )
            logger.debug(
                "Processed batch %d: %d rows.",
                batch_number,
                batch.table.num_rows,
            )

            yield batch
