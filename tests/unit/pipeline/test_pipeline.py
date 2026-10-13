from collections.abc import Callable, Iterable
from typing import Any

import pyarrow as pa
import pytest

from etlrelay.core import Batch
from etlrelay.pipeline import Pipeline


def make_batch(value: int) -> Batch:
    """Create a batch containing one integer value."""
    return Batch(table=pa.table({"value": [value]}))


def make_schema_batch(
    schema: pa.Schema,
    rows: list[dict[str, Any]],
) -> Batch:
    """Create a batch with an explicit Arrow schema."""
    return Batch(table=pa.Table.from_pylist(rows, schema=schema))


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


class RecordingProcessor:
    def __init__(self):
        self.batches: list[Batch] = []

    def process(self, batch: Batch) -> Batch:
        self.batches.append(batch)
        return batch


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

    def test_pipeline_passes_zero_row_batch_to_processor_and_sink(self):
        schema = pa.schema([pa.field("id", pa.int64(), nullable=False)])
        table = pa.Table.from_pylist([], schema=schema)
        batch = Batch(table=table)

        source = StubSource([batch])
        processor = RecordingProcessor()
        sink = CollectingSink()

        pipeline = Pipeline(source, [processor], sink)

        pipeline.run()

        assert source.read_calls == 1

        assert len(processor.batches) == 1
        assert processor.batches[0] is batch

        assert sink.write_calls == 1
        assert len(sink.batches) == 1
        assert sink.batches[0] is batch

        assert sink.batches[0].table.num_rows == 0
        assert sink.batches[0].table.schema.equals(schema)

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
        processor = RecordingProcessor()
        sink = CollectingSink()

        pipeline = Pipeline(source, [processor], sink)

        pipeline.run()

        assert source.read_calls == 1
        assert processor.batches == []
        assert sink.write_calls == 0
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
        assert [get_batch_value(batch) for batch in sink.batches] == [1]

    def test_pipeline_propagates_processor_error(self):
        class FailingProcessor:
            def process(self, batch: Batch) -> Batch:
                raise RuntimeError("Processor failed")

        source = StubSource([make_batch(1)])
        sink = CollectingSink()
        pipeline = Pipeline(source, [FailingProcessor()], sink)

        with pytest.raises(RuntimeError, match="Processor failed"):
            pipeline.run()
        assert sink.write_calls == 0

    def test_pipeline_propagates_sink_error(self):
        class FailingSink:
            def write(self, batches: Iterable[Batch]) -> None:
                raise RuntimeError("Sink failed")

        source = StubSource([make_batch(1)])
        pipeline = Pipeline(source, [], FailingSink())

        with pytest.raises(RuntimeError, match="Sink failed"):
            pipeline.run()

    @pytest.mark.parametrize(
        "difference",
        ["field_names", "field_order", "field_types", "nullability"],
    )
    def test_rejects_incompatible_output_schema_before_sink_write(
        self,
        difference: str,
    ):
        id_field = pa.field("id", pa.int64(), nullable=False)
        name_field = pa.field("name", pa.string(), nullable=False)

        first_schema = pa.schema([id_field, name_field])
        first_batch = make_schema_batch(
            first_schema,
            [{"id": 1, "name": "Ada"}],
        )

        if difference == "field_names":
            second_schema = pa.schema(
                [
                    pa.field("identifier", pa.int64(), nullable=False),
                    name_field,
                ]
            )
            second_rows = [{"identifier": 2, "name": "Sam"}]

        elif difference == "field_order":
            second_schema = pa.schema([name_field, id_field])
            second_rows = [{"id": 2, "name": "Sam"}]

        elif difference == "field_types":
            second_schema = pa.schema(
                [
                    pa.field("id", pa.string(), nullable=False),
                    name_field,
                ]
            )
            second_rows = [{"id": "2", "name": "Sam"}]

        else:
            second_schema = pa.schema(
                [
                    pa.field("id", pa.int64(), nullable=True),
                    name_field,
                ]
            )
            second_rows = [{"id": 2, "name": "Sam"}]

        second_batch = make_schema_batch(second_schema, second_rows)
        sink = CollectingSink()

        pipeline = Pipeline(
            StubSource([first_batch, second_batch]),
            [],
            sink,
        )

        with pytest.raises(ValueError, match="(?i)schema"):
            pipeline.run()

        # The first batch was written; the incompatible batch was not.
        assert sink.write_calls == 1
        assert len(sink.batches) == 1
        assert sink.batches[0].table.to_pylist() == [{"id": 1, "name": "Ada"}]

    def test_ignores_schema_and_field_metadata_differences(self):
        first_schema = pa.schema(
            [
                pa.field(
                    "id",
                    pa.int64(),
                    nullable=False,
                    metadata={b"origin": b"source-a"},
                )
            ],
            metadata={b"version": b"1"},
        )
        second_schema = pa.schema(
            [
                pa.field(
                    "id",
                    pa.int64(),
                    nullable=False,
                    metadata={b"origin": b"source-b"},
                )
            ],
            metadata={b"version": b"2"},
        )

        batches = [
            make_schema_batch(first_schema, [{"id": 1}]),
            make_schema_batch(second_schema, [{"id": 2}]),
        ]
        sink = CollectingSink()

        pipeline = Pipeline(StubSource(batches), [], sink)
        pipeline.run()

        assert len(sink.batches) == 2
        assert [batch.table.column("id").to_pylist() for batch in sink.batches] == [[1], [2]]

    def test_rejects_incompatible_schema_on_zero_row_batch(self):
        first_schema = pa.schema([pa.field("id", pa.int64(), nullable=False)])
        second_schema = pa.schema([pa.field("id", pa.string(), nullable=False)])

        batches = [
            make_schema_batch(first_schema, [{"id": 1}]),
            make_schema_batch(second_schema, []),
        ]
        sink = CollectingSink()

        pipeline = Pipeline(StubSource(batches), [], sink)

        with pytest.raises(ValueError, match="(?i)schema"):
            pipeline.run()

        assert len(sink.batches) == 1
        assert sink.batches[0].table.column("id").to_pylist() == [1]

    def test_accepts_different_input_schemas_when_outputs_are_compatible(self):
        from etlrelay.processors import SelectColumns

        id_field = pa.field("id", pa.int64(), nullable=False)

        first_schema = pa.schema(
            [
                id_field,
                pa.field("name", pa.string(), nullable=False),
            ]
        )
        second_schema = pa.schema(
            [
                id_field,
                pa.field("active", pa.bool_(), nullable=False),
            ]
        )

        batches = [
            make_schema_batch(
                first_schema,
                [{"id": 1, "name": "Ada"}],
            ),
            make_schema_batch(
                second_schema,
                [{"id": 2, "active": True}],
            ),
        ]
        sink = CollectingSink()

        pipeline = Pipeline(
            StubSource(batches),
            [SelectColumns(columns=["id"])],
            sink,
        )
        pipeline.run()

        assert [batch.table.to_pylist() for batch in sink.batches] == [
            [{"id": 1}],
            [{"id": 2}],
        ]

        expected_schema = pa.schema([id_field])
        assert all(batch.table.schema.equals(expected_schema) for batch in sink.batches)
