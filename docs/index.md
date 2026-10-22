# ETLRelay

ETLRelay is an open-source Python framework for composing lightweight, batch-oriented extract, transform, and load (ETL) pipelines.

Its core execution model is:

```text
Source → Processor(s) → Sink
```

A source produces batches, processors transform them, and a sink consumes the processed output. File workflows keep storage access independent of format-specific reading and writing.

## v1.0.1 — Community Standards and Contribution Guidance

ETLRelay v1.0.1 is a documentation-only patch release that builds on the
stable public contracts established in v1.0.0.

This release introduces:

- A Code of Conduct establishing community participation expectations
  and reporting procedures.
- Contribution guidelines covering development practices, quality
  requirements, and pull request workflows.
- An accessibility statement outlining accessibility considerations,
  known limitations, and feedback procedures.
- GitHub issue templates for bug reports and feature requests.
- A pull request template covering testing, documentation, compatibility,
  and security considerations.

**No runtime functionality, public Python APIs, CLI behavior, YAML configuration
schema, or dependencies have changed from v1.0.0.**

Install the current release:

```bash
pip install etlrelay==1.0.1
```

Start with [Getting Started](getting-started.md), the
[compatibility policy](compatibility.md), and the
[v1.0.1 release notes](development/release-notes-v1.0.1.md).

See the [v1.0.1 release notes](development/release-notes-v1.0.1.md)
for details about the Community Standards and documentation changes.

Applications upgrading from v1.0.0 require no code or configuration
migration. For releases before v0.9.0, see the
[migration guide](development/migration-v0.9.0.md).

## Current Capabilities

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

SQLite is the reference SQL integration-test backend. Other SQLAlchemy
dialects require appropriate drivers and application-level verification.

ETLRelay supports CPython 3.12, 3.13, and 3.14.

The complete test suite runs on Python 3.12, with installed
wheel/source-distribution compatibility checks across the declared
Python/platform matrix.

See the [packaging verification record](development/packaging-verification.md)
for verification evidence.

The [v1.0.0 readiness record](development/release-v1.0.0.md) documents
the verification and release gates used to establish the initial stable
public contract.

## Documentation

- [Getting Started](getting-started.md) — create and run YAML- or Python-defined pipelines.
- [CLI Reference](cli-reference.md) — command usage, validation, execution, and exit codes.
- [YAML Configuration](configuration.md) — schema version `1`, supported properties, preflight behavior, and limitations.
- [Core Concepts](concepts.md) — batches, processors, schemas, and file formats.
- [Compatibility Policy](compatibility.md) — stable public contracts, versioning, and compatibility guarantees.
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
- [Roadmap](roadmap.md) — released milestones and future development considerations.

## Contributing and Community

ETLRelay welcomes contributions that improve reliability, documentation,
testing, and supported functionality.

Development follows test-driven practices, with an emphasis on explicit
component contracts, maintainability, and incremental improvements.

### Contributing

See the
[Contribution Guidelines](https://github.com/apaquette/ETLRelay/blob/main/CONTRIBUTING.md)
for instructions on:

- Setting up the development environment.
- Working with the `dev` development branch.
- Running tests and quality checks.
- Following architecture and coding guidelines.
- Preparing and submitting pull requests.

Significant features or architectural changes should be discussed
through a GitHub issue before implementation.

### Reporting Bugs and Requesting Features

Use [GitHub Issues](https://github.com/apaquette/ETLRelay/issues)
to report defects or propose enhancements.

The repository provides dedicated templates for:

- **Bug reports** — reproducible failures, expected behavior,
  environment details, and relevant diagnostic output.
- **Feature requests** — use cases, proposed behavior, alternatives,
  and compatibility considerations.

[Create a new issue](https://github.com/apaquette/ETLRelay/issues/new/choose).

### Code of Conduct

All contributors and community participants are expected to follow
the project's
[Code of Conduct](https://github.com/apaquette/ETLRelay/blob/main/CODE_OF_CONDUCT.md).

The Code of Conduct establishes expectations for respectful
participation and provides procedures for reporting unacceptable behavior.

### Security Reporting

Potential security vulnerabilities must not be disclosed through
public GitHub issues.

Follow the private reporting instructions in the
[Security Policy](https://github.com/apaquette/ETLRelay/blob/main/SECURITY.md).

### Accessibility

ETLRelay aims to make its documentation, command-line interface,
and contribution process accessible.

See the
[Accessibility Statement](https://github.com/apaquette/ETLRelay/blob/main/ACCESSIBILITY.md)
for accessibility considerations, known limitations, and reporting procedures.

## Scope and Limitations

YAML schema version `1` supports file and SQL sources/sinks, local
CSV/Parquet workflows, and the built-in `select_columns`,
`rename_columns`, and `filter_rows` processors.

The configuration model uses explicit registrations rather than
arbitrary dynamic imports or a general-purpose plugin system.

The `validate` command parses and validates configuration without
constructing runtime components, resolving SQL environment variables,
or executing the pipeline.

Builder preflight occurs during `run`; neither validation nor preflight
guarantees runtime data compatibility, filesystem availability, or
database connectivity.

File writes are non-atomic, and SQL sink transactions operate per
nonempty batch. ETLRelay does not automatically retry failed operations
or roll back earlier persisted output.

S3, HDFS, and other remote-storage integrations are not included in
the current supported feature set. Their future development remains
subject to separate roadmap decisions.

Public interfaces follow the [compatibility policy](compatibility.md).
Users remain responsible for evaluating deployment security and
operational requirements.