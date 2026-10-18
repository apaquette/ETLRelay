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

Storage provides binary streams; readers and writers handle file formats.

```text
FileSource → FileSystem → BinaryIO → Reader → Batch

Batch iterable → Writer → BinaryIO → FileSystem → Destination
```

`FileSource` composes a filesystem with a reader. `FileSink` composes a filesystem with a writer. This separates resource access from format-specific parsing and serialization.

The built-in local storage and tabular formats are `LocalFileSystem`, CSV, and Parquet. Select the reader and writer explicitly when composing `FileSource` and `FileSink`; the file extension does not select a format automatically.

## CSV and Parquet Behavior

| Behavior | CSV | Parquet |
|---|---|---|
| Representation | Text; no embedded Arrow schema | Columnar binary format with schema and type information |
| Reading types | PyArrow infers types from text; exact schema round trips are not guaranteed | Preserves supported schema/type information represented in the file |
| Multiple batches | Serializes batches in order; a CSV stream has one header written by the first batch | Serializes batches in order into one Parquet file |
| Zero-row batch with schema | Can write a header-only CSV | Writes a valid schema-bearing zero-row Parquet file; the reader yields an empty batch with the schema |
| Empty batch iterable | Writes no bytes | Raises `WriterError` because no schema is available to initialize the file |
| Stream requirements | Binary stream | Reader requires a seekable binary stream; writer requires a writable binary stream supported by PyArrow |

A zero-row batch and an empty batch iterable are different: the former still carries an Arrow schema; the latter carries no batch from which a schema can be obtained. `ParquetWriter` uses the first batch's schema and requires following batches to have the same schema. ETLRelay does not merge incompatible schemas or automatically cast batches.

The component that opens a stream retains responsibility for its lifecycle; readers and writers must not close caller-owned streams.

## Declarative Configuration

ETLRelay 0.6.0 adds schema-versioned YAML configuration as an alternative to direct Python composition. The supported configuration surface is deliberately fixed: file and SQL sources/sinks, local storage, CSV/Parquet file formats, and the built-in column-selection, renaming, and row-filtering processors.

The workflow is:

```text
YAML file
   ↓
ConfigLoader + KeyValueReader/YamlReader
   ↓
ConfigValidator
   ↓
Validated mapping
   ↓
PipelineBuilder + shared ComponentCatalog
   ↓
Pipeline
   ↓
Pipeline.run()
```

A mapping-shaped configuration document is not a tabular `Batch` stream. `KeyValueReader` is a separate protocol from the current tabular `Reader` protocol. `YamlReader` handles YAML syntax and document shape; `ConfigValidator` handles ETLRelay's schema; `PipelineBuilder` resolves explicit registrations and constructs runtime components. Neither loading nor schema validation builds or executes a pipeline.

Configuration schema version `1` requires exactly `version`, `source`, `processors`, and `sink`. Unknown fields and unsupported component types are rejected. SQL source/sink connection URLs are referenced by environment-variable name, then checked during builder preflight before component factories and source/sink I/O begin. See [YAML Configuration](configuration.md) for properties, combinations, errors, and examples.

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

Schema metadata differences are ignored when checking compatibility. Schema validation takes place after all configured processors have run. This allows processors to normalize inputs with different schemas into compatible output schemas.

If a processed batch has an incompatible schema, the pipeline raises `ValueError` before yielding that batch to the sink. The pipeline does not automatically merge schemas, cast values, or reconcile incompatible outputs. Zero-row batches participate in schema validation just like non-empty batches.

### Empty Sources and Zero-Row Batches

An empty source iterable and a zero-row batch represent different conditions.

- **Zero-row batch:** The source produces a `Batch` containing a zero-row Arrow table. The batch passes through the configured processors, participates in schema validation, and is delivered to the sink if processing succeeds.
- **Empty source iterable:** The source produces no batches. No processors are called, and the sink is not invoked.

The presence of a batch, rather than its row count, determines whether the pipeline has data to process.

### Exceptions and Partial Writes

Exceptions raised while reading from a source, iterating over its batches, processing a batch, validating its output schema, or writing to a sink propagate to the caller. ETLRelay does not wrap these errors in a separate pipeline exception hierarchy.

If a later batch fails, batches successfully written before the failure are not automatically rolled back. The pipeline does not provide transactional execution across multiple batches.

## Current Scope

ETLRelay provides synchronous, batch-oriented execution with local CSV/Parquet I/O, SQLAlchemy-backed SQL sources/sinks, a small set of built-in processors, and YAML-driven construction. SQLite is the reference SQL integration-test backend; other SQLAlchemy dialects require appropriate drivers and independent verification. SQL sink tables must already exist and be compatible with the output columns.

S3, HDFS, and other remote-storage backends remain outside the planned v1.0.0 scope. Scheduling, distributed execution, parallel processing, automatic retries, generic plugins, and automatic schema reconciliation are not provided by the current implementation. Additional capabilities should be introduced only when concrete requirements justify them.
