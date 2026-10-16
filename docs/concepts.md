# Core Concepts

ETLRelay composes batch-oriented ETL pipelines from a source, an ordered sequence of processors, and a sink.

```text
Source → Processor(s) → Sink
```

A source produces batches, processors transform them, and a sink consumes the processed output. For file workflows, ETLRelay separates storage access from format-specific reading and writing.

## Components

### Batch

A `Batch` wraps a `pyarrow.Table` and provides the common tabular data representation used throughout ETLRelay.

The table retains its values and Arrow schema, including field names, field order, data types, and nullability. A processor may change the schema as part of a transformation; otherwise, the schema is preserved.

A batch containing zero rows is still a valid batch. Its schema remains available even when it contains no data rows.

### Source, Processor, and Sink

A `Source` implements `read()` and produces an iterable of batches.

A `Processor` implements:

```python
process(batch: Batch) -> Batch
```

Processors operate on individual batches. The pipeline applies them in their configured order, passing each processor's output to the next processor. ETLRelay includes processors for selecting columns, renaming columns, and filtering rows. Applications can also provide implementations that satisfy the processor contract.

A `Sink` consumes an iterable of processed batches. A file sink composes a storage implementation with a writer to write batches to a configured destination.

### Storage and File Formats

Storage provides binary streams; readers and writers handle the file format.

```text
FileSource → FileSystem → BinaryIO → Reader → Batch

Batch iterable → Writer → BinaryIO → FileSystem → Destination
```

`FileSource` composes a filesystem with a reader. `FileSink` composes a filesystem with a writer. This separates resource access from format-specific parsing and serialization.

The current implementation supports local filesystem access through `LocalFileSystem`, with CSV through `CsvReader`/`CsvWriter` and Parquet through `ParquetReader`/`ParquetWriter`. Select the reader and writer explicitly when constructing `FileSource` and `FileSink`; the file extension does not select a format automatically.

## CSV and Parquet Behavior

The file format is selected when composing the source or sink. `FileSource` and `FileSink` do not inspect the filename extension or choose a reader/writer automatically.

| Behavior | CSV | Parquet |
| --- | --- | --- |
| Representation | Text; no embedded Arrow schema | Columnar binary format with schema and type information |
| Reading types | PyArrow infers types from text; exact schema round trips are not guaranteed | Preserves schema and supported Arrow types represented in the Parquet file |
| Multiple batches | Serializes batches in order; a CSV stream has one header written by the first batch | Serializes batches in order into one Parquet file |
| Zero-row batch with schema | Can write a header-only CSV | Writes a valid schema-bearing zero-row Parquet file; the reader yields one empty batch with the schema |
| Empty batch iterable | Writes no bytes | Raises `WriterError` because no schema is available to initialize the file |
| Stream requirements | Binary stream | Reader: seekable binary stream; writer: writable binary stream supported by PyArrow |

A zero-row batch and an empty batch iterable are different: the former still carries an Arrow schema; the latter carries no batch from which a schema can be obtained. `ParquetWriter` uses the first batch's schema and requires following batches to have the same schema. ETLRelay does not merge incompatible schemas or automatically cast batches.

Parquet preserves supported Arrow schema/type information and values for the types handled by the installed PyArrow version; this should not be read as a guarantee that every Arrow-specific type, extension type, or metadata field is losslessly represented by Parquet. The stream protocols use `BinaryIO`, which does not express seekability in its type signature. `ParquetReader` therefore has a stronger runtime requirement than the generic `Reader` protocol suggests. The caller/component that opens a stream retains responsibility for its lifecycle; readers and writers must not close caller-owned streams.


## Pipeline Execution

`Pipeline` coordinates the source, processors, and sink. Execution is synchronous, and batches are processed sequentially in source order.

The pipeline does not buffer all source batches before writing. Processed batches are yielded incrementally to the sink.

### Output Schema Compatibility

The first processed output batch establishes the expected schema for a pipeline run. Every subsequent processed output batch must have a compatible schema.

Compatibility requires matching:

- Field names
- Field order
- Arrow field types
- Field nullability

Schema metadata differences are ignored when checking compatibility.

Schema validation takes place after all configured processors have run. This allows processors to normalize inputs with different schemas into compatible output schemas.

If a processed batch has an incompatible schema, the pipeline raises `ValueError` before yielding that batch to the sink. The pipeline does not automatically merge schemas, cast values, or reconcile incompatible outputs.

Zero-row batches participate in schema validation just like non-empty batches.

### Empty Sources and Zero-Row Batches

An empty source iterable and a zero-row batch represent different conditions.

- **Zero-row batch:** The source produces a `Batch` containing a zero-row Arrow table. The batch passes through the configured processors, participates in schema validation, and is delivered to the sink if processing succeeds.
- **Empty source iterable:** The source produces no batches. No processors are called, and the sink is not invoked.

The presence of a batch, rather than its row count, determines whether the pipeline has data to process.

### Exceptions and Partial Writes

Exceptions raised while reading from a source, iterating over its batches, processing a batch, validating its output schema, or writing to a sink propagate to the caller. ETLRelay does not wrap these errors in a separate pipeline exception hierarchy.

If a later batch fails, batches successfully written before the failure are not automatically rolled back. The pipeline does not provide transactional execution across multiple batches.


## SQL Sources and Sinks

`SqlSource` and `SqlSink` are direct implementations of the `Source` and `Sink` contracts. They do not route database I/O through `FileSystem`, `Reader`, or `Writer` components.

`SqlSource` executes a SQLAlchemy text query. Supply values through the optional `parameters` mapping, using named bind markers such as `:status`. A non-empty result becomes one Arrow-backed `Batch`; an empty query result produces no batches. The current source materializes query results in memory, so it is not a streaming or paginated reader.

`SqlSink` appends rows to a destination table that must already exist. It reflects the table and validates batch column names before inserting. It does not create/replace a table, update or upsert rows, migrate a schema, or retry a failed operation. Destination columns omitted from a batch must be satisfied by defaults/nullability or database constraints will fail.

The SQLAlchemy `Engine` is created and owned by the caller. ETLRelay closes the query connection/result and the sink's per-batch transaction contexts; it does not dispose the engine. SQLite is the repeatable integration backend. Other SQLAlchemy dialects need their driver and application-level validation.

**Transactions are per non-empty sink batch.** A successful batch is committed independently; a later failure does not roll back earlier batches. Empty query results produce no batches, and `SqlSink` skips explicitly supplied zero-row batches.

Bound parameters apply to query values, not SQL identifiers or arbitrary SQL syntax. `SqlSink` delegates destination table identifier handling to SQLAlchemy's table reflection/insert APIs. Since `SqlSource` accepts caller-authored SQL text, callers must not interpolate untrusted input into it and must validate or allowlist any dynamic identifiers.

`replace`, ORM models, schema migrations, automatic retries, and a pipeline-wide transaction are not supported. See [SQL source and sink architecture](architecture/sql_source_and_sink.md) for the full contract.

## Current Scope

ETLRelay provides synchronous, batch-oriented pipeline execution with local CSV/Parquet I/O, SQL input/output, and a small set of built-in processors.

The local storage contract, including binary stream modes, path containment,
error propagation, output creation, overwrite behavior, and stream cleanup,
is documented in the [local filesystem architecture](architecture/local_filesystem.md).

S3, HDFS, and other remote-storage backends are outside the v0.4.0 milestone
and planned v1.0.0 scope. Additional storage and platform integrations may
be reviewed after v1.0.0 if concrete requirements justify them. No
particular backend or delivery date is promised.

Scheduling, distributed execution, parallel processing, automatic retries,
and automatic schema reconciliation are not provided by the current
pipeline implementation. Additional capabilities should be introduced
when concrete requirements justify them and their scope is established.