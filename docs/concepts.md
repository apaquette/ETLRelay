# Core Concepts

## Batch

A `Batch` is the unit of tabular data passed through a pipeline. The initial implementation uses Apache Arrow to represent tabular data. Readers produce batches, processors transform batches, and writers consume them.

## Source

A source implements `read()` and produces an iterable of batches. A file source composes a storage implementation with a reader.

## Processor

A processor implements `process(batch)` and returns the batch to be passed to the next processor. The pipeline applies processors in their configured order. The initial release does not require a built-in transformation library; applications can provide processor implementations satisfying the protocol.

## Sink

A sink consumes an iterable of processed batches. A file sink composes a storage implementation with a writer and writes the batches to one configured destination.

## Storage versus file format

Storage provides a binary stream; the reader or writer handles the format:

```text
FileSource → FileSystem.open_read() → BinaryIO → Reader → Batch
Batch iterable → Writer → BinaryIO → FileSystem.open_write() → destination
```

The initial concrete storage implementation is `LocalFileSystem`. The initial format implementation is CSV. Other storage backends and formats can be added independently when supported.

## Pipeline execution

`Pipeline` coordinates a source, a sequence of processors, and a sink. Execution is synchronous and exceptions propagate to the caller. The initial release does not provide scheduling, distributed execution, parallel processing, automatic retries, or a web interface.

## Batch and Empty-Data Semantics

### Batch Representation

`Batch` is the common tabular data representation used throughout ETLRelay. It wraps a `pyarrow.Table` and exposes the underlying table through the `table` property.

`Batch` does not convert or reconstruct the table. The table retains its values and Arrow schema, including field names, field order, data types, and nullability.

A batch containing zero rows is still a valid batch. Its schema remains available even when it contains no data rows.

### Empty Source Iterables

An empty source iterable and a zero-row batch represent different conditions:

- **Zero-row batch:** The source produces a `Batch` containing a zero-row Arrow table. The batch passes through the configured processors and is delivered to the sink.
- **Empty source iterable:** The source produces no batches. The pipeline does not call any processors or invoke the sink.

The presence of a batch, rather than its row count, determines whether the pipeline has data to process.

### Pipeline Execution

`Pipeline` processes batches sequentially and applies configured processors in their declared order. Each processor receives the preceding processor's output.

Processed batches are passed to the sink through an iterable. The pipeline does not buffer all source batches before processing them.

The sink is invoked once when at least one successfully processed batch is available. It is not invoked when the source produces no batches.

### Exception Propagation

Exceptions raised while reading from a source, iterating over its batches, processing a batch, or writing to a sink propagate to the caller. The pipeline does not wrap these exceptions in a separate pipeline exception hierarchy.

When an error occurs after processing has begun, batches already consumed or written are not automatically rolled back. The pipeline does not provide transactional execution across multiple batches.

### Contract Summary

| Condition | Expected behavior |
|---|---|
| Normal batch | Values and Arrow schema remain intact unless a processor changes them. |
| Zero-row batch | Processes as a batch and reaches the sink. |
| Empty source iterable | No processor calls and no sink invocation. |
| Multiple batches | Processed sequentially and delivered in source order. |
| Multiple processors | Applied in configured order to each batch. |
| Source or processor exception | Propagates to the caller. |
| Sink exception | Propagates to the caller. |
| Error after earlier batches were written | Earlier writes are not automatically rolled back. |
