import logging
from collections.abc import Callable, Iterable, Iterator
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pyarrow as pa
import pytest

from etlrelay.core import Batch
from etlrelay.pipeline import Pipeline
from etlrelay.security import PathValidator
from etlrelay.sinks import FileSink
from etlrelay.sources.file import FileSource
from etlrelay.storage import LocalFileSystem
from etlrelay.writers import CsvWriter


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

    def test_pipeline_logs_execution_lifecycle(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Log pipeline start and successful completion at INFO."""
        source = StubSource([make_batch(10)])
        sink = CollectingSink()
        pipeline = Pipeline(source, [], sink)

        with caplog.at_level(
            logging.INFO,
            logger="etlrelay.pipeline.pipeline",
        ):
            pipeline.run()

        messages = [
            record.message
            for record in caplog.records
            if record.name == "etlrelay.pipeline.pipeline" and record.levelno == logging.INFO
        ]

        assert messages == [
            "Pipeline execution started.",
            "Pipeline execution completed.",
        ]

        assert sink.write_calls == 1
        assert len(sink.batches) == 1

    def test_empty_pipeline_logs_successful_completion(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Treat an empty source as a successful pipeline execution."""
        source = StubSource([])
        sink = CollectingSink()
        pipeline = Pipeline(source, [], sink)

        with caplog.at_level(
            logging.INFO,
            logger="etlrelay.pipeline.pipeline",
        ):
            pipeline.run()

        messages = [
            record.message
            for record in caplog.records
            if record.name == "etlrelay.pipeline.pipeline" and record.levelno == logging.INFO
        ]

        assert messages == [
            "Pipeline execution started.",
            "Pipeline execution completed.",
        ]

        assert sink.write_calls == 0

    def test_pipeline_logs_batch_progress_at_debug(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Log processed batch counts without exposing record values."""
        secret = "private-customer-information"

        first_batch = Batch(table=pa.table({"value": [secret]}))
        second_batch = Batch(table=pa.table({"value": [secret, "another-value"]}))

        source = StubSource([first_batch, second_batch])
        sink = CollectingSink()
        pipeline = Pipeline(source, [], sink)

        with caplog.at_level(
            logging.DEBUG,
            logger="etlrelay.pipeline.pipeline",
        ):
            pipeline.run()

        debug_messages = [
            record.message
            for record in caplog.records
            if record.name == "etlrelay.pipeline.pipeline" and record.levelno == logging.DEBUG
        ]

        assert debug_messages == [
            "Processed batch 1: 1 rows.",
            "Processed batch 2: 2 rows.",
        ]

        assert secret not in caplog.text
        assert "another-value" not in caplog.text

        assert len(sink.batches) == 2

    def test_pipeline_failure_preserves_exception_without_logging_payload(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Preserve the original error without logging its sensitive message."""
        secret = "private-source-value"
        original_error = RuntimeError(f"Source failed: {secret}")

        def failing_batches() -> Iterable[Batch]:
            yield make_batch(10)
            raise original_error

        source = StubSource(failing_batches())
        sink = CollectingSink()
        pipeline = Pipeline(source, [], sink)

        with caplog.at_level(
            logging.DEBUG,
            logger="etlrelay.pipeline.pipeline",
        ):
            with pytest.raises(RuntimeError) as exc_info:
                pipeline.run()

        assert exc_info.value is original_error

        messages = [
            record.message
            for record in caplog.records
            if record.name == "etlrelay.pipeline.pipeline"
        ]

        assert "Pipeline execution started." in messages
        assert "Processed batch 1: 1 rows." in messages
        assert "Pipeline execution completed." not in messages

        assert secret not in caplog.text
        assert sink.write_calls == 1

    def test_sink_failure_does_not_log_successful_completion(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Do not report completion when the sink fails."""
        original_error = RuntimeError("Sink failed")

        class FailingSink:
            def write(self, batches: Iterable[Batch]) -> None:
                list(batches)
                raise original_error

        source = StubSource([make_batch(10)])
        pipeline = Pipeline(source, [], FailingSink())

        with caplog.at_level(
            logging.INFO,
            logger="etlrelay.pipeline.pipeline",
        ):
            with pytest.raises(RuntimeError) as exc_info:
                pipeline.run()

        assert exc_info.value is original_error

        messages = [
            record.message
            for record in caplog.records
            if record.name == "etlrelay.pipeline.pipeline"
        ]

        assert messages == ["Pipeline execution started."]


@pytest.mark.parametrize("sink_fails", [False, True])
def test_pipeline_closes_file_source_when_sink_stops_early(
    sink_fails: bool,
) -> None:
    """Close the active source when a sink stops consuming batches."""
    batch = Batch(table=pa.table({"id": [1, 2]}))

    stream = BytesIO(b"unused")

    storage = Mock()
    storage.open_read.return_value = stream

    reader = Mock()
    reader.read.return_value = iter([batch, batch])

    source = FileSource(
        path="input.csv",
        storage=storage,
        reader=reader,
    )

    class EarlyStopSink:
        def __init__(self) -> None:
            self.batches: Iterable[Batch] | None = None

        def write(self, batches: Iterable[Batch]) -> None:
            # Retain the iterable so garbage collection cannot hide
            # a missing explicit close.
            self.batches = batches

            # Consume only the first batch.
            next(iter(batches))

            if sink_fails:
                raise RuntimeError("Sink failed")

    sink = EarlyStopSink()
    pipeline = Pipeline(source, [], sink)

    if sink_fails:
        with pytest.raises(RuntimeError, match="Sink failed"):
            pipeline.run()
    else:
        pipeline.run()

    assert sink.batches is not None
    assert stream.closed

    storage.open_read.assert_called_once_with("input.csv")


def test_pipeline_preserves_sink_failure_when_source_cleanup_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Preserve the sink error when iterator cleanup also fails."""
    batch = Batch(table=pa.table({"id": [1]}))

    sink_error = RuntimeError("primary-sink-failure")
    cleanup_error = RuntimeError("secret-cleanup-failure")

    class FailingSourceIterator:
        def __init__(self) -> None:
            self.closed = False
            self.yielded = False

        def __iter__(self):
            return self

        def __next__(self) -> Batch:
            if self.yielded:
                raise StopIteration

            self.yielded = True
            return batch

        def close(self) -> None:
            self.closed = True
            raise cleanup_error

    source_iterator = FailingSourceIterator()

    source = Mock()
    source.read.return_value = source_iterator

    sink = Mock()
    sink.write.side_effect = sink_error

    pipeline = Pipeline(source, [], sink)

    with caplog.at_level(
        logging.WARNING,
        logger="etlrelay.pipeline.pipeline",
    ):
        with pytest.raises(RuntimeError) as exc_info:
            pipeline.run()

    assert exc_info.value is sink_error
    assert source_iterator.closed

    assert "Pipeline iterator cleanup failed (RuntimeError)." in caplog.text
    assert "secret-cleanup-failure" not in caplog.text
    assert "primary-sink-failure" not in caplog.text


def test_pipeline_propagates_source_cleanup_failure_after_success(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Propagate a cleanup failure when pipeline execution succeeds."""
    batch = Batch(table=pa.table({"id": [1]}))
    cleanup_error = RuntimeError("secret-cleanup-failure")

    class FailingCloseIterator:
        def __init__(self) -> None:
            self._batches = iter([batch, batch])
            self.closed = False

        def __iter__(self) -> Iterator[Batch]:
            return self

        def __next__(self) -> Batch:
            return next(self._batches)

        def close(self) -> None:
            self.closed = True
            raise cleanup_error

    source_iterator = FailingCloseIterator()

    source = Mock()
    source.read.return_value = source_iterator

    sink = Mock()

    pipeline = Pipeline(source, [], sink)

    with caplog.at_level(
        logging.DEBUG,
        logger="etlrelay.pipeline.pipeline",
    ):
        with pytest.raises(RuntimeError) as exc_info:
            pipeline.run()

    assert exc_info.value is cleanup_error
    assert source_iterator.closed

    sink.write.assert_called_once()

    assert "Pipeline iterator cleanup failed (RuntimeError)." in caplog.text
    assert "secret-cleanup-failure" not in caplog.text
    assert "Pipeline execution completed." not in caplog.text


def test_pipeline_attempts_all_iterator_cleanup_after_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Attempt every cleanup and preserve the first cleanup exception."""
    batch = Batch(table=pa.table({"id": [1]}))

    processing_error = RuntimeError("secret-processing-cleanup")
    source_error = RuntimeError("secret-source-cleanup")

    class FailingCloseIterator:
        def __init__(self, error: RuntimeError) -> None:
            self._batches = iter([batch])
            self.error = error
            self.close_calls = 0

        def __iter__(self) -> Iterator[Batch]:
            return self

        def __next__(self) -> Batch:
            return next(self._batches)

        def close(self) -> None:
            self.close_calls += 1
            raise self.error

    source_iterator = FailingCloseIterator(source_error)
    processing_iterator = FailingCloseIterator(processing_error)

    source = Mock()
    source.read.return_value = source_iterator

    sink = Mock()
    pipeline = Pipeline(source, [], sink)

    monkeypatch.setattr(
        pipeline,
        "_process_batches",
        lambda _: processing_iterator,
    )

    with caplog.at_level(
        logging.DEBUG,
        logger="etlrelay.pipeline.pipeline",
    ):
        with pytest.raises(RuntimeError) as exc_info:
            pipeline.run()

    # Cleanup occurs in reverse order.
    # The first cleanup exception takes precedence.
    assert exc_info.value is processing_error

    # A failure closing the processing iterator must not prevent
    # the source iterator from being closed.
    assert processing_iterator.close_calls == 1
    assert source_iterator.close_calls == 1

    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.WARNING and record.name == "etlrelay.pipeline.pipeline"
    ]

    assert warnings == [
        "Pipeline iterator cleanup failed (RuntimeError).",
        "Pipeline iterator cleanup failed (RuntimeError).",
    ]

    assert "secret-processing-cleanup" not in caplog.text
    assert "secret-source-cleanup" not in caplog.text
    assert "Pipeline execution completed." not in caplog.text


def test_empty_pipeline_preserves_existing_file(
    tmp_path: Path,
) -> None:
    """Do not open or truncate a destination when no batches are produced."""
    output_path = tmp_path / "output.csv"
    original_content = b"existing output must remain unchanged"
    output_path.write_bytes(original_content)

    storage = LocalFileSystem(
        path_validator=PathValidator(base_path=tmp_path),
    )

    sink = FileSink(
        path="output.csv",
        storage=storage,
        writer=CsvWriter(),
    )

    pipeline = Pipeline(
        source=StubSource([]),
        processors=[],
        sink=sink,
    )

    pipeline.run()

    assert output_path.read_bytes() == original_content


def test_zero_row_first_batch_establishes_output_schema() -> None:
    """Validate later batches against a schema established by zero rows."""
    expected_schema = pa.schema([pa.field("id", pa.int64(), nullable=False)])

    incompatible_schema = pa.schema([pa.field("id", pa.string(), nullable=False)])

    first_batch = Batch(table=pa.Table.from_pylist([], schema=expected_schema))

    second_batch = Batch(
        table=pa.Table.from_pylist(
            [{"id": "2"}],
            schema=incompatible_schema,
        )
    )

    sink = CollectingSink()

    pipeline = Pipeline(
        source=StubSource([first_batch, second_batch]),
        processors=[],
        sink=sink,
    )

    with pytest.raises(
        ValueError,
        match="Incompatible output schema",
    ):
        pipeline.run()

    assert sink.write_calls == 1

    assert len(sink.batches) == 1
    assert sink.batches[0] is first_batch
    assert sink.batches[0].table.num_rows == 0


def test_schema_failure_preserves_partially_written_file(
    tmp_path: Path,
) -> None:
    """A later schema failure does not roll back earlier file output."""
    first_batch = Batch(
        table=pa.table(
            {
                "id": pa.array([1], type=pa.int64()),
            }
        )
    )

    incompatible_batch = Batch(
        table=pa.table(
            {
                "id": pa.array(["two"], type=pa.string()),
            }
        )
    )

    output_path = tmp_path / "output.csv"
    output_path.write_bytes(b"previous content")

    sink = FileSink(
        path="output.csv",
        storage=LocalFileSystem(
            path_validator=PathValidator(base_path=tmp_path),
        ),
        writer=CsvWriter(),
    )

    pipeline = Pipeline(
        source=StubSource([first_batch, incompatible_batch]),
        processors=[],
        sink=sink,
    )

    with pytest.raises(
        ValueError,
        match="Incompatible output schema",
    ):
        pipeline.run()

    content = output_path.read_text(encoding="utf-8")

    assert '"id"' in content
    assert "1" in content
    assert "two" not in content

    assert "previous content" not in content
