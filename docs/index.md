# ETLRelay

ETLRelay is a lightweight Python framework for composing batch-oriented extract, transform, and load (ETL) pipelines.

Its core execution model is:

```text
Source → Processor(s) → Sink
```

For file workflows, storage access and file-format handling are separate concerns. A file source composes a storage implementation with a reader; a file sink composes storage with a writer. This keeps the core pipeline independent of filesystem and serialization details.


## Current release scope

The `0.5.0` release extends ETLRelay's tested local CSV/Parquet pipeline model with SQL input and append-only SQL output through SQLAlchemy.

Current capabilities include:

- An Arrow-backed `Batch` model and synchronous source → processor(s) → sink execution.
- Local filesystem access through `FileSystem` and `LocalFileSystem`.
- CSV and Parquet readers/writers composed through `FileSource` and `FileSink`.
- Built-in column selection, column renaming, and row filtering processors.
- `SqlSource` for parameterized SQL queries and `SqlSink` for append-only writes to existing SQL tables.
- Unit, integration, round-trip, and functional tests for component behavior and composed local-file/SQLite pipelines.

SQLite is the repeatable SQL integration-test backend. Other SQLAlchemy dialects require their appropriate drivers and application-level verification; the project does not claim equal integration coverage for every database. SQL output tables must exist before a pipeline runs. `SqlSink` does not create or migrate tables, replace existing data, or retry failed operations.

S3, HDFS, and other remote filesystem/storage backends are outside the planned v1.0.0 scope. Additional storage and platform integrations may be reviewed after v1.0.0 if concrete requirements justify them; no particular backend or delivery date is promised.

ETLRelay remains pre-1.0 software. Its public APIs may evolve between minor releases.

## Documentation

- [Getting Started](getting-started.md) — run local CSV, Parquet, or SQLite SQL pipelines.
- [Concepts](concepts.md) — understand batches, sources, processors, sinks, storage, schema behavior, and file formats.
- [Security](security.md) — understand current path validation and release limitations.
- [API Reference](api-reference.md) — public classes and methods, generated from the Python source documentation.
- [Reader and Writer](architecture/reader_and_writer.md) — file-format behavior, stream requirements, and reader/writer contracts.
- [Development](development.md) — test and build ETLRelay and its documentation.
- [Local filesystem](architecture/local_filesystem.md) — storage contract, local filesystem behavior, error handling, and stream ownership.
- [Path validation](architecture/path_validator.md) — path containment, resolution, and security limitations.
- [SQL source and sink](architecture/sql_source_and_sink.md) — query parameters, identifier handling, append semantics, engine ownership, and transaction boundaries.
- [Roadmap](roadmap.md) — release milestones and the planned v1.0 scope.

> **Release status:** ETLRelay is pre-1.0 software. Its public API is not yet guaranteed to remain stable across minor releases.
