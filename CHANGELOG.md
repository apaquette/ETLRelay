# Changelog

Notable changes to ETLRelay are documented here.

This project follows the principles of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [Unreleased]

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