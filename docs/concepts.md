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
