# ETLRelay

ETLRelay is a lightweight Python framework for composing batch-oriented extract, transform, and load (ETL) pipelines.

Its core execution model is:

```text
Source → Processor(s) → Sink
```

For file workflows, storage access and file-format handling are separate concerns. A file source composes a storage implementation with a reader; a file sink composes storage with a writer. This keeps the core pipeline independent of filesystem and serialization details.

## Current release scope

The `0.3.0` release adds Parquet as a second local file format alongside CSV. Current capabilities include:

- An Arrow-backed `Batch` model.
- Source, processor, and sink contracts with synchronous pipeline execution.
- Local filesystem streams behind a `FileSystem` protocol.
- CSV and Parquet readers/writers composed explicitly through `FileSource` and `FileSink`.
- Built-in column selection, column renaming, and row filtering processors.
- Path containment validation for local filesystem resources.
- Unit, integration, and functional tests for component behavior and composed local pipelines.

SQL support, YAML pipeline configuration, a CLI, remote storage backends, and generic API integrations remain outside this release's scope. ETLRelay remains pre-1.0 software; public APIs may evolve between minor releases.

## Documentation

- [Getting Started](getting-started.md) — run local CSV or Parquet pipelines using the shared composition model.
- [Concepts](concepts.md) — understand batches, sources, processors, sinks, storage, schema behavior, and file formats.
- [Security](security.md) — understand current path validation and release limitations.
- [API Reference](api-reference.md) — public classes and methods, generated from the Python source documentation.
- [Reader and Writer](architecture/reader_and_writer.md) — file-format behavior, stream requirements, and reader/writer contracts.
- [Development](development.md) — test and build ETLRelay and its documentation.

> **Release status:** ETLRelay is pre-1.0 software. Its public API is not yet guaranteed to remain stable across minor releases.
