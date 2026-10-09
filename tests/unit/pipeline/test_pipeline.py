from collections.abc import Callable, Iterable

import pyarrow as pa
import pytest

from etlrelay.core import Batch
from etlrelay.pipeline import Pipeline


def make_batch(value: int) -> Batch:
    """Create a batch containing one integer value."""
    return Batch(table=pa.table({"value": [value]}))


def get_batch_value(batch: Batch) -> int:
    """Extract the integer value from a test batch."""
    return batch.table.column("value")[0].as_py()


class StubSource:
    def __init__(self, batches: Iterable[Batch]):
        self.batches = batches
        self.read_calls = 0

    def read(self) -> Iterable[Batch]:
        self.read_calls += 1
        return self.batches


class CollectingSink:
    def __init__(self):
        self.batches: list[Batch] = []
        self.write_calls = 0

    def write(self, batches: Iterable[Batch]) -> None:
        self.write_calls += 1
        self.batches.extend(batches)


class TransformProcessor:
    def __init__(
        self,
        name: str,
        transform: Callable[[int], int],
        calls: list[str],
    ):
        self.name = name
        self.transform = transform
        self.calls = calls

    def process(self, batch: Batch) -> Batch:
        self.calls.append(self.name)
        return make_batch(self.transform(get_batch_value(batch)))


class TestPipeline:
    def test_pipeline_passes_source_batch_to_sink(self):
        batch = make_batch(10)
        source = StubSource([batch])
        sink = CollectingSink()

        pipeline = Pipeline(source, [], sink)

        pipeline.run()

        assert source.read_calls == 1
        assert sink.write_calls == 1
        assert len(sink.batches) == 1
        assert sink.batches[0] is batch

    def test_pipeline_processes_multiple_batches_in_source_order(self):
        source = StubSource(
            [
                make_batch(10),
                make_batch(20),
                make_batch(30),
            ]
        )
        sink = CollectingSink()

        pipeline = Pipeline(source, [], sink)

        pipeline.run()

        assert [get_batch_value(batch) for batch in sink.batches] == [
            10,
            20,
            30,
        ]

        assert sink.write_calls == 1

    def test_pipeline_applies_processors_in_configured_order(self):
        calls: list[str] = []
        source = StubSource([make_batch(2)])
        sink = CollectingSink()

        processors = [
            TransformProcessor("add", lambda value: value + 3, calls),
            TransformProcessor("multiply", lambda value: value * 4, calls),
            TransformProcessor("subtract", lambda value: value - 1, calls),
        ]

        pipeline = Pipeline(source, processors, sink)

        pipeline.run()

        assert calls == ["add", "multiply", "subtract"]
        assert [get_batch_value(batch) for batch in sink.batches] == [19]

    def test_pipeline_applies_processors_to_each_batch(self):
        calls: list[str] = []
        source = StubSource([make_batch(1), make_batch(2)])
        sink = CollectingSink()

        processors = [
            TransformProcessor("add", lambda value: value + 1, calls),
            TransformProcessor("multiply", lambda value: value * 2, calls),
        ]

        pipeline = Pipeline(source, processors, sink)

        pipeline.run()

        assert calls == ["add", "multiply", "add", "multiply"]
        assert [get_batch_value(batch) for batch in sink.batches] == [
            4,
            6,
        ]

    def test_pipeline_with_no_processors_passes_batches_unchanged(self):
        batches = [make_batch(10), make_batch(20)]
        source = StubSource(batches)
        sink = CollectingSink()

        pipeline = Pipeline(source, [], sink)

        pipeline.run()

        assert len(sink.batches) == len(batches)
        assert all(
            actual is expected for actual, expected in zip(sink.batches, batches, strict=True)
        )

    def test_pipeline_handles_empty_source(self):
        source = StubSource([])
        sink = CollectingSink()

        pipeline = Pipeline(source, [], sink)

        pipeline.run()

        assert source.read_calls == 1
        assert sink.write_calls == 1
        assert sink.batches == []

    def test_pipeline_propagates_source_error(self):
        class FailingSource:
            def read(self) -> Iterable[Batch]:
                raise RuntimeError("Source failed")

        sink = CollectingSink()
        pipeline = Pipeline(FailingSource(), [], sink)

        with pytest.raises(RuntimeError, match="Source failed"):
            pipeline.run()

        assert sink.write_calls == 0

    def test_pipeline_propagates_error_during_source_iteration(self):
        def failing_batches() -> Iterable[Batch]:
            yield make_batch(1)
            raise RuntimeError("Source iteration failed")

        source = StubSource(failing_batches())
        sink = CollectingSink()
        pipeline = Pipeline(source, [], sink)

        with pytest.raises(RuntimeError, match="Source iteration failed"):
            pipeline.run()

        assert sink.write_calls == 1

    def test_pipeline_propagates_processor_error(self):
        class FailingProcessor:
            def process(self, batch: Batch) -> Batch:
                raise RuntimeError("Processor failed")

        source = StubSource([make_batch(1)])
        sink = CollectingSink()
        pipeline = Pipeline(source, [FailingProcessor()], sink)

        with pytest.raises(RuntimeError, match="Processor failed"):
            pipeline.run()

    def test_pipeline_propagates_sink_error(self):
        class FailingSink:
            def write(self, batches: Iterable[Batch]) -> None:
                raise RuntimeError("Sink failed")

        source = StubSource([make_batch(1)])
        pipeline = Pipeline(source, [], FailingSink())

        with pytest.raises(RuntimeError, match="Sink failed"):
            pipeline.run()
