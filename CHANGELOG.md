# Changelog

Notable changes to ETLRelay are documented here.

This project follows the principles of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).


## [0.9.0] - YYYY-MM-DD

### Changed

- Remove the unused Polars runtime dependency; the frozen implementation uses PyArrow.
- Verify wheel and source-distribution installation in separate environments across
  the declared CI matrix and existing release workflows.
- Renamed the public `Reader` and `Writer` protocols to `TabularReader`
  and `TabularWriter`. The modules remain `etlrelay.core.reader` and
  `etlrelay.core.writer`; the former class names are removed without aliases.
  Applications must update imported class names and type annotations.
- Retained `KeyValueReader` as the separate contract for mapping-shaped
  documents. Configuration loading continues to depend on this abstraction.

### Fixed

- Preserve the original serialization or upstream batch failure when Parquet
  finalization also fails; log secondary cleanup failures without their messages.
  Finalization-only failures continue to propagate.
- Report invalid YAML document shapes as configuration failures (CLI exit code
  `3`) through `YamlDocumentError`, a backward-compatible `ValueError` subclass.
- Reject ambiguous requested columns in `SelectColumns` with `ValueError`.
- Reject duplicate final names in `RenameColumns`, including duplicate input fields.
- Correct tabular protocol references, validation behavior, and SQL resource
  ownership documentation; restore strict API documentation builds.

### Testing

- Compare complete runtime dependency constraints in wheel and sdist metadata,
  verify licence/notice inclusion, and exercise public imports and direct
  CSV/Parquet/SQLite composition from installed artifacts.
- Audit the failure and cleanup matrix; cover borrowed streams after failures,
  processor failures before and during output, SQL connection/conversion failures,
  malformed SQL connection check-in, and controlled CLI connection diagnostics.
- Verify processed Parquet-to-SQLite and SQLite-to-Parquet pipelines through
  the built and installed CLI, reusing the existing isolated-wheel fixture.
- Strengthen schema assertions for the existing YAML source/sink matrix and
  the direct Parquet processor chain, including types, nullability, and nulls.
- Record the representative Python, YAML, and installed-CLI pipeline coverage
  matrix without duplicating every combination at each test layer.

### Documentation

- Complete a self-contained YAML/Python quick start with explicit published versus
  candidate installation instructions and bounded CPython requirements.
- Add v0.9.0 migration guidance and draft release notes; retain schema version 1
  and document removed protocol names, corrected failures, and dependency changes.
- Verify all maintained Python/YAML examples and the quick-start code against a
  built, installed candidate outside the checkout using the existing CLI fixture.
- Add an application-defined processor example, contributor guidance, expected
  demo outputs, SQL reset instructions, and troubleshooting guidance.
- Align API, architecture, configuration, logging, security, and release docs;
  consolidate duplicate release instructions into the existing canonical page.

### Scope Decisions

- Deferred `KeyValueWriter` because the v1.0 feature set does not require
  mapping-document serialization.
- Deferred public tabular/row-record conversion utilities pending a
  concrete use case and defined conversion semantics.

## [0.8.0] - 2026-10-20

### Security

- Strengthen and verify local filesystem path-containment behavior, including traversal and symbolic-link escape handling.
- Clarify that path containment does not provide operating-system sandboxing or eliminate time-of-check/time-of-use races.
- Strengthen SQL connection environment-variable validation and preflight contracts, rejecting literal connection URLs where environment-variable identifiers are required.
- Standardize controlled operational logging and CLI error reporting to avoid routinely exposing SQL connection URLs, parameters, record contents, and sensitive exception messages.
- Add regression coverage for sensitive-output handling during configuration and runtime failures.
- Update the locked `certifi` dependency from `2026.7.22` to `2026.10.19` to address reported certificate-authority security advisories.

### Reliability and Resource Lifecycle

- Ensure `Pipeline.run()` attempts deterministic cleanup of active processing and source iterators on completion, early sink termination, and execution failure.
- Preserve original execution exceptions when iterator cleanup also fails, reporting secondary cleanup failures through controlled warnings.
- Verify file stream closure during normal execution and reader/writer failures while preserving caller ownership of borrowed streams.
- Verify SQL connection and result cleanup and retain caller ownership of directly supplied SQLAlchemy engines.
- Clarify the lifecycle of engines owned by the shared SQL engine factory for configuration-built pipelines.
- Ensure successful SQL batch-commit logging occurs only after successful transaction completion.

### Operational Contracts

- Verify that entirely empty pipeline sources do not invoke sinks or modify existing output files.
- Confirm that zero-row batches participate in pipeline schema validation.
- Verify schema compatibility for field names, order, Arrow types, and nullability while permitting schema metadata differences.
- Confirm CSV and Parquet empty-input behavior and SQL sink handling of zero-row batches.
- Verify file overwrite and failure semantics, including truncation of existing output and potentially partial files after failed writes.
- Confirm that SQL sink transactions are scoped to individual nonempty batches and that earlier committed batches are not rolled back by later failures.
- Expand regression coverage for schema mismatches, failure propagation, and resource cleanup.

### CI and Distribution Integrity

- Add explicit dependency lockfile verification and known-vulnerability auditing to CI.
- Add installed dependency consistency checks.
- Verify built wheel and source-distribution metadata, package contents, runtime dependency declarations, and CLI entry points.
- Strengthen installed-wheel import isolation and distribution-version verification.
- Extend clean-environment installed CLI testing, including configuration validation and representative CSV pipeline execution.
- Add a compatibility matrix covering Ubuntu, macOS, and Windows using the same built wheel.
- Retain the full test and quality suite on Ubuntu with Python 3.12 without duplicating it across every compatibility target.

### Compatibility and Development

- Declare CPython `>=3.12,<3.15` as the supported interpreter range.
- Verify installed-wheel operation on Python 3.13 and 3.14 in addition to the Python 3.12 baseline.
- Establish Python 3.12 as the default development interpreter through `.python-version`.
- Extend the Nix development environment with Python 3.13 and 3.14 for compatibility checks.
- Provide Nix-managed Node.js for Pyright execution.
- Confirm that Python 3.11 is not currently supported because the implementation uses Python 3.12-specific generic type syntax.

### Documentation

- Update security documentation to distinguish tested controls from operating-system and application responsibilities.
- Clarify configuration validation, SQL environment-variable preflight, and their runtime limitations.
- Document operational logging, error propagation, exception precedence, and redaction boundaries.
- Document file and SQL resource ownership, empty-input handling, schema validation, transactions, and partial-write behavior.
- Update the API reference and architecture documentation to match verified component contracts.
- Expand development and release instructions to cover dependency integrity, distribution verification, and installed-wheel compatibility.
- Update the README and documentation homepage for the v0.8.0 release.

### Limitations

- ETLRelay does not provide a complete filesystem sandbox, secrets vault, SQL authorization layer, or unrestricted execution environment for untrusted components.
- File output does not provide atomic replacement or automatic restoration after failure.
- SQL transactions operate per nonempty batch; pipeline-wide transactions, automatic retries, and rollback of earlier committed output are not supported.
- Built-in error-reporting protections do not guarantee sanitization of all third-party exceptions or externally configured logs.
- SQLite remains the reference SQL integration-test backend; other SQLAlchemy dialects require independent verification.
- S3, HDFS, and other remote-storage integrations remain outside the planned v1.0.0 scope.

### API and Configuration Compatibility

- Retain YAML configuration schema version `1`.
- Retain the existing CLI commands and primary Python component interfaces.
- No new source, sink, storage backend, processor type, or configuration schema version is introduced by this release.

## [0.7.1] - 2026-10-20

### Documentation

- Updated `docs/index.md` to reflect the CLI functionality introduced in v0.7.0.
- Added the CLI Reference to the documentation index, covering command usage, configuration validation, pipeline execution, and exit codes.
- Removed the outdated statement that a command-line interface remained planned for a later milestone.
- Clarified the supported scope of the CLI and the existing version 1 YAML configuration format.

### Compatibility

- Documentation-only release. No runtime code, public APIs, CLI behavior, or configuration schema changes.

## [0.7.0] - 2026-10-19

### Added

- Add the `etlrelay` command-line interface with `run`, `validate`, `version`, and `help` commands.
- Add an installed-package and subprocess test path for the CLI, including local CSV execution and output verification.
- Add functional and integration coverage for command exit codes, standard streams, validation side effects, runtime failures, and sensitive-output regression checks.
- Add CLI reference documentation and CLI usage to the getting-started guide.

### Changed

- Refactor CLI command handling into `CliApplication`, with thin Typer command adapters and injected service factories.
- Share configuration loading and validation behavior between `run` and `validate`.
- Define CLI exit codes for unexpected errors (`1`), usage errors (`2`), configuration/build failures (`3`), and runtime/cleanup failures (`4`).

## [0.6.0] - 2026-10-18

### Added

- Add safe YAML configuration loading through `KeyValueReader` and `YamlReader`, including single-document root-mapping validation and duplicate mapping-key rejection.
- Add versioned configuration schema validation for schema version `1`, including root/section rules, component-specific validators, path-qualified diagnostics, and aggregated `ConfigurationError` failures.
- Add explicit `ComponentRegistration` and `ComponentRegistry` contracts that associate component validators with runtime factories.
- Add `TabularFileFormatRegistry` capability checks that distinguish readable and writable formats.
- Add `ComponentCatalog` and `create_default_component_catalog()` to compose shared storage, format, source, sink, and processor registries plus the SQL engine factory.
- Add `PipelineBuilder` to resolve component registrations, preflight SQL environment references, construct components in YAML order, and return a runtime `Pipeline` without executing it.
- Add `SqlEngineFactory` support for resolving connection URLs from environment variables, creating/caching SQLAlchemy engines on demand, redacting credential-bearing values from its errors, and disposing owned engines during cleanup.
- Add end-to-end and integration coverage for YAML/direct-Python equivalence, processor ordering, file and SQLite source/sink combinations, and invalid-config/missing-variable rejection before component factory invocation or source/sink I/O.
- Document the versioned YAML contract, supported property/component matrix, environment-variable references, secret-handling constraints, validation boundaries, and configuration-driven examples.

### Changed

- Keep configuration-document parsing, schema validation, component construction, and pipeline execution as separate responsibilities.
- Share the default component registries between validation and construction so supported component names cannot silently diverge between these stages.
- Update project documentation and roadmap to reflect YAML configuration and runtime construction as implemented in v0.6.0. The CLI remains planned for v0.7.0.

### Configuration contract and limitations

- Schema version `1` requires exactly `version`, `source`, `processors`, and `sink`; the version must be the integer `1`. Unknown top-level and component properties are rejected, and `processors: []` is valid.
- The supported source types are `file` and `sql`; sink types are `file` and `sql`; storage is `local`; file formats are `csv` and `parquet`; processors are `select_columns`, `rename_columns`, and `filter_rows`.
- SQL `connection_url_env` fields contain environment-variable names, not connection URLs. Missing/empty variables fail during builder preflight before component factories and source/sink operations. The engine factory avoids including resolved URLs or credentials in its own errors.
- SQL sinks append to existing tables and do not create, replace, truncate, or migrate them. SQLite is the reference integration-test backend; other SQLAlchemy dialects require appropriate drivers and independent verification.
- Direct Python composition remains supported. Direct `SqlSource`/`SqlSink` callers retain ownership of the supplied engine; the shared engine factory lifecycle applies to configuration-built pipelines.

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
- `SqlSink` appends to an existing table. It does not create a table, replace a table, update or upsert existing rows, or manage schema migrations.
- Each non-empty batch written by `SqlSink` has its own transaction. A later failed batch does not roll back previously committed batches.
- The caller owns the SQLAlchemy `Engine`; source connections and results are closed by the component, and sink transaction contexts are closed per batch.
- Query values must be supplied through SQLAlchemy bound parameters. Identifiers in source query text remain part of the caller-authored SQL; dynamic identifiers require trusted construction or validation.
- SQLite is the repeatable integration-test backend. Other database dialects require the matching driver and independent verification.
- `replace`, ORM models, schema migrations, and automatic retries are not supported.

## [0.4.0] - 2026-10-14

### Changed

- Stabilize and document the `FileSystem` contract for binary stream ownership, error propagation, path handling, output creation, overwrite semantics, and cleanup.
- Normalize missing local input files to `FileSystemError`, including the case where a file disappears between path validation and opening.
- Document the shared storage/source/sink composition used by local CSV and Parquet pipelines.

### Documentation

- Clarify the local filesystem contract, public API, and current v1.0 storage scope.
- Explicitly exclude S3, HDFS, and other remote-storage implementations from v0.4.0 and the planned v1.0 scope.

## [0.3.0] - 2026-10-14

### Added

- Add `ParquetReader` and `ParquetWriter` as implementations of the existing reader and writer protocols.
- Support local Parquet input and output through `FileSource`, `FileSink`, and `LocalFileSystem`.
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
