# Changelog

Notable changes to ETLRelay are documented here.

This project follows the principles of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [0.5.0] - 2026-10-16

### Added

- Add `SqlSource` and `SqlSink` as SQLAlchemy-backed implementations of the core source and sink contracts, separate from file storage and reader/writer abstractions.
- Support bound query-value parameters in `SqlSource` and conversion of non-empty query results into Arrow-backed batches.
- Support append-only writes from batches into existing SQL tables, with SQLAlchemy table reflection and per-batch transactions.
- Add SQLite integration coverage for SQL reads/writes, SQL round trips, and mixed file/SQL functional pipelines.
- Document SQL API contracts, connection ownership, identifier handling, empty-data behavior, transaction boundaries, supported database scope, and limitations.
- Add a runnable in-memory SQLite pipeline example without real credentials.

### Behavior and limitations

- `SqlSource` returns no batches when a query returns no rows; a non-empty query result is materialized as one batch.
- `SqlSink` appends to an existing table. It does not create or replace tables, update existing rows, or manage schema migrations.
- Each non-empty batch written by `SqlSink` has its own transaction. A later failed batch does not roll back previously committed batches.
- The caller owns the SQLAlchemy `Engine`; source connections and results are closed by the component, and sink transaction contexts are closed per batch.
- Query values must be supplied through SQLAlchemy bound parameters. Identifiers in source query text remain part of the caller-authored SQL; dynamic identifiers require trusted construction or validation.
- SQLite is the repeatable integration-test backend. Other database dialects require their SQLAlchemy dialect/driver and are not implied to have equivalent integration coverage.
- `replace`, ORM models, schema migrations, and automatic retries are not supported.

## [0.4.0] - 2026-10-14

### Changed

- Stabilize and document the `FileSystem` contract for binary stream
  ownership, error propagation, path handling, output creation, overwrite
  semantics, and cleanup.
- Normalize missing local input files to `FileSystemError`, including the
  case where a file disappears between path validation and opening.
- Document the shared storage/source/sink composition used by local CSV
  and Parquet pipelines.

### Documentation

- Clarify the local filesystem contract, public API, and current v1.0
  storage scope.
- Explicitly exclude S3, HDFS, and other remote-storage implementations
  from v0.4.0 and the planned v1.0 scope.

## [0.3.0] - 2026-10-14

### Added

- Add `ParquetReader` and `ParquetWriter` as implementations of the existing reader and writer protocols.
- Support local Parquet input and output through `FileSource`, `FileSink`, and `LocalFileSystem`, without format-specific branches in source/sink orchestration.
- Add Parquet unit, integration, round-trip, and functional pipeline coverage, including schema/type preservation, nulls, and zero-row files.
- Add a runnable local Parquet pipeline example.

### Changed

- Update user-facing documentation to describe CSV and Parquet support through the shared file composition model.

### Compatibility notes

- CSV is text-based and does not carry Arrow type metadata. CSV reads infer types, so an exact Arrow schema round trip is not guaranteed.
- `ParquetWriter` derives the output schema from the first batch. An empty iterable raises `WriterError`; a zero-row batch with a schema is valid.
- `ParquetReader` requires a seekable binary stream for the PyArrow Parquet API. Stream lifecycle remains the caller's responsibility.

## [0.2.0] - 2026-10-13

### Added

- Add `SelectColumns` to select columns in a requested order, rejecting duplicate and unknown column names.
- Add `RenameColumns` to rename columns while validating unknown source columns, duplicate destination names, and naming conflicts.
- Add `FilterRows` with support for `==`, `!=`, `<`, `<=`, `>`, and `>=` comparison operators.
- Add an end-to-end local CSV transformation workflow demonstrating column selection, renaming, filtering, and writing results.

### Changed

- Enforce output schema compatibility across batches within a pipeline run. Field names, field order, Arrow types, and nullability must match the first processed output batch. Schema metadata differences are ignored.
- Reject incompatible output batches with `ValueError` before they reach the sink. Batches successfully written before a later failure are not rolled back.

### Compatibility notes

- `FilterRows` excludes rows whose comparison evaluates to null.
- Incompatible comparison types raise `TypeError`; automatic custom casting is not performed.
- Zero-row batches retain their schema and participate in pipeline output schema validation.

## [0.1.4] - 2026-10-09

### Changed

- Update the supported PyArrow dependency range to `>=23.0.1,<24`.
- Update the pytest development dependency constraint as part of dependency maintenance.

### Fixed

- Update dependencies to mitigate package vulnerabilities.
- Configure the Nix development shell's runtime library path for native library loading.

## [0.1.3] - 2026-10-09

### Added

- Expose core contracts and components through package-level imports, including the core interfaces, pipeline, readers, writers, sources, sinks, storage, and security components.

### Changed

- Update implementation modules, tests, documentation, and examples to use the package-level imports.

## [0.1.2] - 2026-10-09

### Added

- Configure Mermaid diagram rendering in the MkDocs documentation.

## [0.1.1] - 2026-10-09

### Fixed

- Correct a documentation link in the README.

## [0.1.0] - 2026-10-09

### Added

- Batch-oriented pipeline contracts for sources, processors, and sinks.
- An Arrow-backed `Batch` representation.
- Synchronous pipeline execution with processors applied in sequence.
- Local filesystem access through a stream-based `FileSystem` protocol and `LocalFileSystem` implementation.
- CSV reading and writing through separate reader and writer components.
- `FileSource` and `FileSink` composition of storage and format components.
- Path containment validation for local filesystem paths.
- Unit, integration, and functional tests for the initial local CSV pipeline.

### Notes

- This is an experimental pre-1.0 release. Public APIs may change between minor releases.
- The initial implementation focuses on local filesystem and CSV workflows. SQL, declarative YAML configuration, a CLI, Parquet, remote storage backends, and generic API integrations are outside the scope of this release.