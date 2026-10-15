# ETLRelay

ETLRelay is a lightweight Python framework for composing batch-oriented extract, transform, and load (ETL) pipelines.

Its core execution model is:

```text
Source → Processor(s) → Sink
```

For file workflows, storage access and file-format handling are separate concerns. A file source composes a storage implementation with a reader; a file sink composes storage with a writer. This keeps the core pipeline independent of filesystem and serialization details.


## Current release scope

The `0.4.0` release stabilizes the storage contract used by ETLRelay's
existing local-file pipelines. The milestone documents and verifies the
behavior of local storage without introducing a new storage backend.

Current capabilities include:

- An Arrow-backed `Batch` model.
- Source, processor, and sink contracts with synchronous pipeline execution.
- Local filesystem streams through the `FileSystem` protocol and
  `LocalFileSystem`.
- CSV and Parquet readers and writers composed explicitly through
  `FileSource` and `FileSink`.
- Built-in column selection, column renaming, and row filtering processors.
- Local path containment validation.
- Unit, integration, and functional tests for component behavior and
  composed local pipelines.

The supported storage implementation is the local filesystem. S3, HDFS,
and other remote-storage backends are outside v0.4.0 and the planned
v1.0.0 scope. Additional storage and platform integrations may be reviewed
after v1.0.0 based on concrete requirements, without a commitment to
specific backends or release dates.

SQL support, YAML pipeline configuration, and a CLI belong to later
milestones. They are not part of the v0.4.0 storage-contract release.

ETLRelay remains pre-1.0 software. Its public APIs may evolve between
minor releases.


## Documentation

- [Getting Started](getting-started.md) — run local CSV or Parquet pipelines using the shared composition model.
- [Concepts](concepts.md) — understand batches, sources, processors, sinks, storage, schema behavior, and file formats.
- [Security](security.md) — understand current path validation and release limitations.
- [API Reference](api-reference.md) — public classes and methods, generated from the Python source documentation.
- [Reader and Writer](architecture/reader_and_writer.md) — file-format behavior, stream requirements, and reader/writer contracts.
- [Development](development.md) — test and build ETLRelay and its documentation.
- [Local filesystem](architecture/local_filesystem.md) — storage contract, local filesystem behavior, error handling, and stream ownership.
- [Path validation](architecture/path_validator.md) — path containment, resolution, and security limitations.
- [Roadmap](roadmap.md) — release milestones and the planned v1.0 scope.

> **Release status:** ETLRelay is pre-1.0 software. Its public API is not yet guaranteed to remain stable across minor releases.
