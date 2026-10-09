# ETLRelay

ETLRelay is a lightweight Python framework for composing batch-oriented extract, transform, and load (ETL) pipelines.

Its core execution model is:

```text
Source → Processor(s) → Sink
```

For file workflows, storage access and file-format handling are separate concerns. A file source composes a storage implementation with a reader; a file sink composes storage with a writer. This keeps the core pipeline independent of filesystem and serialization details.

## Current release scope

The planned `0.1.0` release is experimental and focuses on the initial local CSV pipeline:

- An Arrow-backed `Batch` model.
- Source, processor, and sink contracts with synchronous pipeline execution.
- Local filesystem streams behind a `FileSystem` protocol.
- CSV reading and writing through separate components.
- Path containment validation for local filesystem resources.
- Unit, integration, and functional tests.

SQL support, YAML pipeline configuration, a CLI, Parquet, remote storage backends, and generic API integrations are outside the initial release scope unless they have been implemented and verified separately.

## Documentation

- [Getting Started](getting-started.md) — run a local CSV-to-CSV pipeline.
- [Concepts](concepts.md) — understand batches, sources, processors, sinks, storage, and readers/writers.
- [Security](security.md) — understand current path validation and release limitations.
- [API Reference](api-reference.md) — generated from the Python source documentation.
- [Development](development.md) — test and build ETLRelay and its documentation.

> **Release status:** ETLRelay is pre-1.0 software. Its public API is not yet guaranteed to remain stable across minor releases.
