# ETLRelay

ETLRelay is an open-source Python framework for composing lightweight, batch-oriented extract, transform, and load (ETL) pipelines.

Its core execution model is:

```text
Source → Processor(s) → Sink
```

A source produces batches, processors transform them, and a sink consumes the processed output. File workflows keep storage access independent of format-specific reading and writing.

## Development milestone: v0.9.0 (unreleased)

This documentation targets the feature-complete beta candidate on `dev`.
The latest published release is v0.8.0; package metadata remains `0.8.0` until
beta preparation assigns the release version. Use a locally built archive to
verify candidate behavior rather than reinstalling the published package.

v0.9.0 freezes local CSV/Parquet and SQLite-based SQL workflows, the existing
processors, YAML schema version 1, and CLI execution. It completes tabular
protocol naming and reviews API contracts, failures, and installation.

Start with [Getting Started](getting-started.md),
[Migration](development/migration-v0.9.0.md), and the
[draft release notes](development/release-notes-v0.9.0.md).

## Current capabilities

ETLRelay includes:

- Arrow-backed `Batch` data and synchronous pipeline execution.
- The `etlrelay` CLI with `run`, `validate`, `version`, and `help` commands.
- Local filesystem access with resolved-path containment validation.
- CSV and Parquet reading and writing.
- Column selection, column renaming, and row filtering processors.
- SQLAlchemy-backed `SqlSource` and append-only `SqlSink`.
- YAML configuration schema version `1` with explicit component validation.
- `ComponentCatalog` and `PipelineBuilder` for configuration-built pipelines.
- Resource lifecycle management and documented error propagation.
- Unit, integration, functional, and installed-distribution tests.

SQLite is the reference SQL integration-test backend. Other SQLAlchemy dialects require appropriate drivers and application-level verification.

ETLRelay supports CPython 3.12, 3.13, and 3.14. The complete test suite runs on Python 3.12, with installed wheel/source-distribution compatibility checks across the declared Python/platform matrix. See the [packaging verification record](development/packaging-verification.md) for verification evidence and outstanding CI gates.

## Documentation

- [Getting Started](getting-started.md) — create and run YAML- or Python-defined pipelines.
- [CLI Reference](cli-reference.md) — command usage, validation, execution, and exit codes.
- [YAML Configuration](configuration.md) — schema version `1`, supported properties, preflight behavior, and limitations.
- [Core Concepts](concepts.md) — batches, processors, schemas, and file formats.
- [Security](security.md) — implemented controls, security boundaries, and deferred risks.
- [Logging](logging.md) — operational events, logging configuration, and error reporting.
- [API Reference](api-reference.md) — public Python interfaces and implementations.
- [Development](development.md) — development environment and verification commands.
- [Release Automation](development/release-automation.md) — CI checks and publication workflow.
- [Pipeline Architecture](architecture/pipeline.md) — execution, schema validation, and iterator cleanup.
- [Configuration Loading](architecture/configuration-loading.md) — loading, validation, construction, and execution boundaries.
- [Configuration Validation](architecture/configuration-validation.md) — schema and component validation.
- [Component Registry](architecture/component-registry.md) — registrations, factories, and component catalog.
- [TabularReader and TabularWriter Contracts](architecture/reader_and_writer.md) — stream ownership and format behavior.
- [SQL Source and Sink](architecture/sql_source_and_sink.md) — SQL parameterization, resources, and transactions.
- [Roadmap](roadmap.md) — released milestones and the remaining v1.0 roadmap.

## Scope and limitations

YAML schema version `1` supports file and SQL sources/sinks, local CSV/Parquet workflows, and the built-in `select_columns`, `rename_columns`, and `filter_rows` processors.

The configuration model uses explicit registrations rather than arbitrary dynamic imports or a general-purpose plugin system.

The `validate` command checks configuration and construction without executing the data pipeline. Runtime failures remain possible because successful preflight does not guarantee data compatibility, filesystem availability, or database connectivity.

File writes are non-atomic, and SQL sink transactions operate per nonempty batch. ETLRelay does not automatically retry failed operations or roll back earlier persisted output.

S3, HDFS, and other remote-storage integrations remain outside the planned v1.0.0 scope.

ETLRelay is experimental pre-1.0 software. Its public APIs may evolve, and users should assess deployment security and operational requirements before processing sensitive or production data.