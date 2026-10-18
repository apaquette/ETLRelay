# ETLRelay

ETLRelay is a lightweight Python framework for composing batch-oriented extract, transform, and load (ETL) pipelines.

Its core execution model is:

```text
Source → Processor(s) → Sink
```

A source produces batches, processors transform them, and a sink consumes the processed output. For file workflows, storage access is independent of format-specific reading and writing.

## Current release: 0.6.0

ETLRelay 0.6.0 adds declarative, versioned YAML configuration while preserving direct Python composition. The YAML configuration path loads and validates a mapping-shaped document, resolves explicit built-in component registrations, preflights required SQL connection-variable references, and then builds a runtime pipeline.

Capabilities include:

- Arrow-backed `Batch` data and synchronous pipeline execution.
- Local filesystem access with path-containment validation.
- CSV and Parquet file input/output.
- Built-in column selection, column renaming, and row filtering processors.
- SQLAlchemy-backed `SqlSource` and append-only `SqlSink`.
- YAML schema version 1, strict configuration validation, and path-qualified validation errors.
- A shared default component catalog and `PipelineBuilder` for configuration-built pipelines.
- Integration and functional coverage for file, SQLite, and mixed source/sink combinations.

SQLite is the reference SQL integration-test backend. Other SQLAlchemy dialects require their appropriate drivers and application-level verification. SQL sink tables must already exist and accept the output columns. ETLRelay remains pre-1.0 software; public APIs may evolve between minor versions.

## Documentation

- [Getting Started](getting-started.md) — prepare demo data and run YAML- or Python-defined pipelines.
- [YAML Configuration](configuration.md) — schema version 1, properties, supported combinations, environment variables, and errors.
- [Core Concepts](concepts.md) — batches, processors, schema behavior, and file formats.
- [Security](security.md) — path containment, safe YAML parsing, SQL parameterization, and connection-secret handling.
- [API Reference](api-reference.md) — public classes and methods, generated from Python docstrings.
- [Configuration Loading Architecture](architecture/configuration-loading.md) — reading, validation, building, and execution boundaries.
- [Configuration Validation Architecture](architecture/configuration-validation.md) — root and component validation.
- [Component Registry Architecture](architecture/component-registry.md) — registrations, factories, and the default component catalog.
- [Reader and Writer Contracts](architecture/reader_and_writer.md) — tabular streams versus mapping-shaped configuration documents.
- [SQL source and sink](architecture/sql_source_and_sink.md) — direct SQL API behavior, query parameters, engine ownership, and transaction boundaries.
- [Roadmap](roadmap.md) — released milestones and the remaining v1.0 roadmap.

## Scope

The v0.6.0 YAML format supports local CSV/Parquet files and SQL sources/sinks, with `select_columns`, `rename_columns`, and `filter_rows` processors. Schema version 1 has a fixed built-in component set. It is not a general dynamic plugin system. A command-line interface remains planned for a later milestone.
