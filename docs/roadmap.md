# ETLRelay Roadmap: `0.1.0` to `1.0.0`

## Purpose

This roadmap defines incremental, testable milestones from the current YAML-configurable, batch-oriented ETL implementation to a stable ETLRelay `1.0.0` release.

The target for `1.0.0` is a lightweight, synchronous, batch-oriented ETL framework that can read from local files or SQL, apply a small set of transformations, and write to local files or SQL. File storage and serialization remain separate concerns. YAML configuration and a small CLI make pipelines usable without writing Python for every job.

The roadmap is feature-led, not date-led. A version should be released when its acceptance criteria are met; the version numbers are proposed milestones, not a promise to publish every milestone on a fixed schedule.

## Current project status

| Status | Version | Milestone |
|---|---|---|
| Released | `0.1.0` | Experimental local CSV pipeline |
| Released | `0.1.x` | Stabilization and compatible fixes |
| Released | `0.2.0` | Batch contract and built-in processors |
| Released | `0.3.0` | Parquet format support |
| Released | `0.4.0` | Storage contract stabilization |
| Released | `0.5.0` | SQL source and sink |
| Released | `0.6.0` | YAML configuration and runtime pipeline construction |
| Released | `0.7.0` | CLI for validation and execution |
| Released | `0.8.0` | Security, errors, and operational readiness |
| In progress | `0.9.0` | Feature-complete beta and API review |

The latest released milestone is `0.8.0`. It strengthens path validation, configuration preflight, controlled logging and diagnostics, resource cleanup, dependency auditing, distribution verification, and installed-wheel compatibility checks.

Development is now focused on `0.9.0`: freezing the intended v1.0 feature set, completing the protocol naming cleanup, reviewing public contracts, and verifying supported workflows and environments.

The [v1.0 Feature Scope and Support Policy](development/v1-scope.md) defines the frozen feature boundary, release support matrix, deferred capabilities, and required readiness work.

## Versioning policy

ETLRelay is in initial development, so `0.y.z` is appropriate while the public API is still evolving. Semantic Versioning explicitly says that a `0.y.z` public API should not yet be considered stable and recommends `0.1.0` as a reasonable starting point. See [Semantic Versioning 2.0.0](https://semver.org/) and the [Python Packaging User Guide's versioning discussion](https://packaging.python.org/en/latest/discussions/versioning/).

Until `1.0.0`:

- Use a **patch release** such as `0.1.1` for compatible fixes to a published release.
- Use a **minor release** such as `0.2.0` for a coherent feature milestone. Public APIs may still evolve before `1.0.0`, but document notable breaking changes.
- Never replace or modify an already-published release. Publish a new version instead.
- Use a release candidate such as `1.0.0rc1` only when the intended `1.0.0` feature set is complete and the remaining work is validation and defect correction.

## Completed early milestones

### `0.1.0` — Experimental local CSV pipeline (released)

**Outcome:** Published the initial experimental local CSV pipeline. This release established the initial file-to-file execution path; it did not promise API stability.

The original release scope covered:

- `Batch` backed by an Apache Arrow table.
- `Source`, `Processor`, and `Sink` protocols.
- Synchronous `Pipeline` orchestration.
- `PathValidator` for local path containment.
- `FileSystem` protocol and `LocalFileSystem` implementation.
- Stream-based `Reader` and `Writer` protocols.
- `CsvReader` and `CsvWriter`.
- `FileSource` and `FileSink` composed from storage and format components.
- Unit, integration, and functional tests for the local CSV path.
- Architecture and usage documentation that matches the actual implementation.

The original release checks are preserved below as historical reference, not as open tasks for the current milestone.

**Original release checks:**

- Full test suite, Ruff lint/format, and configured Pyright checks.
- Successful source distribution and wheel builds.
- Clean-environment installation and import/usage smoke test.
- Accurate README instructions and example.
- Correct project metadata, licence, package contents, and supported Python version.
- Release notes describing pre-`1.0.0` API evolution.
- Git tag and retained release artifacts.

For future releases, `uv build` is the recommended package-build check. The Python Packaging User Guide describes building source and wheel distributions and supports using TestPyPI to rehearse publication: [Building and Publishing](https://packaging.python.org/en/latest/guides/section-build-and-publish/).

### `0.1.x` — Stabilize the first release (released patch line)

**Goal:** Correct defects found during initial use without expanding the feature set unnecessarily.

Scope:

- Fix defects in the pipeline, batch, path validation, local storage, CSV reading, or CSV writing.
- Improve error messages where they currently obscure the failing operation.
- Correct packaging, installation, documentation, and typing issues.

Do not use patch releases to sneak in unrelated, large features.

## Feature roadmap

### `0.2.0` — Batch contract and built-in processors (released)

**Goal:** Make ETLRelay useful for more than an untransformed file copy.

Scope:

- Document and test `Batch` semantics, including schemas, types, zero-row tables, and empty iterables.
- Define what happens when batches in one output stream have incompatible schemas.
- Add a small set of processors, prioritizing:
  - `SelectColumns`;
  - `RenameColumns`;
  - `FilterRows` with a deliberately limited and documented predicate model.
- Verify processor ordering and behavior across multiple batches.
- Keep the processor interface as `process(batch) -> Batch`.

**Done when:** A tested local CSV pipeline can select, rename, and filter columns/rows while preserving documented schema and empty-batch behavior.

**Not in scope:** A general-purpose expression language, user-supplied code evaluation, or a large processor catalogue.

### `0.3.0` — Parquet format support (released)

**Goal:** Support a second high-value tabular format while retaining the format/storage boundary.

Scope:

- Implement `ParquetReader` and `ParquetWriter` against the existing stream-based reader/writer protocols where the chosen Arrow APIs support that contract.
- Test schema and type preservation, empty data, malformed input, and round trips.
- Verify that the same reader/writer components work with `LocalFileSystem` without special cases in `FileSource` or `FileSink`.
- Document CSV and Parquet behavior, including limitations and format-specific differences.

**Done when:** Local CSV and Parquet sources/sinks work through the same file composition model.

### `0.4.0` — Storage contract stabilization (released)

**Outcome:** Stabilized and documented the `FileSystem`/`LocalFileSystem` contract used by the local-file pipelines. The release specifies stream ownership and cleanup, read/write behavior, missing-path handling, path containment, overwrite behavior, and error propagation.

The release retained local filesystem support only. S3, HDFS, and other remote-storage backends remain outside both the v0.4.0 milestone and the planned v1.0.0 scope. Additional storage/platform integrations may be reviewed after v1.0.0 if concrete requirements justify them; none is promised by this roadmap.

**Done when:** The contract is explicit and tested, `LocalFileSystem` satisfies it, and existing CSV/Parquet pipelines remain functional.

### `0.5.0` — SQL source and sink (released)

**Outcome:** Added SQLAlchemy-backed `SqlSource` and `SqlSink` as direct implementations of the core source/sink contracts, independent of file storage and reader/writer abstractions.

The release supports bound query-value parameters, conversion of query results to Arrow-backed batches, and append-only insertion into existing destination tables. SQLite provides repeatable integration coverage for reads, writes, SQL round trips, and mixed file/SQL functional pipelines.

The caller owns the SQLAlchemy engine. `SqlSource` closes query results/connections after reading; `SqlSink` opens one transaction per non-empty batch. Consequently, earlier batches remain committed if a later batch fails. An empty SQL query returns no batches. The sink skips zero-row batches and requires the destination table to exist with compatible columns.

The SQL API does not implement `replace`, ORM-model integration, table creation/schema migrations, automatic retries, or pipeline-wide transactions. SQLite is the reference integration backend; support for other SQLAlchemy dialects requires the relevant driver and verification.

**Done when:** SQL input and append-only output compose with ETLRelay pipelines, value parameters are bound, and the behavior and limitations are documented and tested.

### `0.6.0` — Declarative YAML configuration (released)

**Outcome:** Added versioned YAML configuration and construction of runtime pipelines from validated mappings while preserving the direct Python APIs.

The release includes:

- `KeyValueReader` and `YamlReader` for safe, mapping-shaped YAML documents, including duplicate-key rejection and root mapping/string-key checks.
- `ConfigLoader` to coordinate configuration file access, parsing, and schema validation.
- `ConfigValidator`, `ConfigurationError`, component-specific validators, and family dispatchers for source, sink, storage, and processor configuration.
- `ComponentRegistry` and `ComponentRegistration` to associate a supported component name with its validator and runtime factory.
- `TabularFileFormatRegistry` capability checks for CSV and Parquet reading/writing.
- `ComponentCatalog` and `create_default_component_catalog()` to compose shared registries, validators, factories, and the SQL engine factory.
- `PipelineBuilder` to resolve all component types and preflight SQL environment-variable references before invoking component factories.
- SQL engine caching, credential-aware error redaction, and explicit builder cleanup for configuration-built pipelines.
- End-to-end tests for YAML/direct-Python equivalence, processor order, supported file/SQLite source-sink combinations, and rejection before external I/O or component construction.
- User-facing documentation for schema version 1, supported properties and combinations, environment-variable references, error handling, architecture, and runnable examples.

Schema version 1 supports file sources/sinks with CSV and Parquet, SQL sources/sinks, local filesystem storage, and the `select_columns`, `rename_columns`, and `filter_rows` processors. It uses explicit registrations only; dynamic plugin loading, arbitrary imports, and `eval` are not supported. Missing or empty SQL environment variables fail during builder preflight before component factory construction and source/sink I/O.

The shared SQL engine factory is owned by the configuration-building lifecycle. Callers close the `PipelineBuilder` after a successfully built pipeline finishes execution. Direct Python SQL components retain their caller-owned engine contract.

**Done when:** A user can define a supported pipeline in YAML, load and validate it, build the same effective pipeline as direct Python composition, execute it, and diagnose configuration/preflight errors without leaking resolved connection URLs. Full regression and release checks pass.

### `0.7.0` — Command-line interface (released)

**Outcome:** Added an installed command-line interface for validating and executing supported YAML pipelines while reusing the existing ETLRelay configuration and execution APIs.

The release includes:

- `etlrelay run PIPELINE` to load, build, and execute a configured pipeline.
- `etlrelay validate PIPELINE` to parse and validate configuration without executing the pipeline.
- `etlrelay version` to print the installed distribution version.
- `etlrelay help [COMMAND]`, root help, and command-specific `--help` options.
- A `CliApplication` class that coordinates command workflows, with thin Typer adapters and injectable service factories.
- Shared configuration loading and validation behavior between `run` and `validate`.
- Documented exit codes: `0` for success, `1` for unexpected internal failures, `2` for usage errors, `3` for configuration/build failures, and `4` for runtime execution or cleanup failures.
- Unit and integration coverage for command outcomes, configuration failures, source/processor/sink errors, and cleanup behavior.
- Functional subprocess tests for the built and installed package, including local CSV output verification and sensitive-output regression checks.
- CLI reference documentation, updated getting-started instructions, and release-check documentation.

The CLI delegates configuration parsing and validation to `ConfigLoader`, component resolution and pipeline construction to the existing catalog and `PipelineBuilder`, and orchestration to `Pipeline`. It does not add scheduling, retries, background execution, or external service dependencies to the core CLI test suite.

**Done when:** A user can install ETLRelay, inspect its CLI help, validate a supported YAML pipeline, and run it end to end from a shell with documented process exit codes and error-output conventions.

### `0.8.0` — Security, errors, and operational readiness

**Goal:** Close cross-cutting gaps before the API is frozen.

Scope:

- Review path containment and local storage behavior, including symlinks and output destinations.
- Review SQL parameterization and identifier validation.
- Validate configuration before side effects occur.
- Establish a small, consistent exception/error-reporting policy without wrapping every error in a generic framework exception.
- Add useful standard-library logging at component boundaries where needed.
- Redact connection secrets, credentials, and sensitive values from errors/logging.
- Document resource/stream ownership, overwrite behavior, empty-batch behavior, and failure propagation.
- Add dependency and package checks to CI.
- Verify the package can be installed and used from its built artifacts, not only from the repository checkout.

**Done when:** Security-relevant behavior is tested at the layer responsible for the risk, and failures are diagnosable without leaking secrets.

### `0.9.0` — Feature-complete beta and API review

**Goal:** Validate the intended v1.0 feature set and stop adding new features.

Scope:

- Feature freeze.
- Review public names, constructors, protocol signatures, configuration schema, CLI behavior, and documented exceptions.
- Complete the pre-`1.0.0` protocol naming cleanup: rename `Reader` and `Writer` to `TabularReader` and `TabularWriter` to make their `Batch`-oriented contracts explicit. Update concrete implementations, type annotations, public exports, tests, examples, and documentation consistently.
- Keep `KeyValueReader` as a separate protocol for mapping-shaped documents. Confirm that configuration loading depends on this abstraction rather than the concrete `YamlReader`.
- Decide whether `KeyValueWriter` has a concrete v1.0 use case before adding it; do not introduce it solely for symmetry.
- Document the distinction between a mapping-shaped document and row records. Review possible tabular-to-records and records-to-tabular conversion contracts before the API freeze, but do not add a generic conversion framework without a demonstrated v1.0 use case.
- Test full pipelines across supported combinations: local CSV, local Parquet, and SQL input/output.
- Test empty inputs, empty batches, schema mismatches, malformed data, inaccessible resources, processor failures, sink failures, and stream cleanup.
- Test a clean install on each supported Python version/platform combination the project claims to support.
- Complete README, quick start, examples, API reference, configuration reference, security notes, contribution instructions, and release notes.
- Document unsupported features and known limitations.

**Done when:** No required v1.0 feature remains unimplemented, release-blocking defects are resolved, and the project can maintain a clear public API contract. Reader/writer names clearly identify tabular contracts, the mapping-document contract is separate, and conversion scope is explicitly documented as either required or deferred.

### `1.0.0rc1` — Release candidate

Cut a release candidate only after `0.9.0` has passed the feature-complete criteria. Use release candidates for final packaging validation, integration feedback, and defect correction—not new features. Publish another candidate if fixes materially affect the release, then proceed to `1.0.0` when the release criteria remain satisfied.

### `1.0.0` — Stable initial release

ETLRelay `1.0.0` is ready when a user can:

1. Install the package using documented instructions.
2. Define a supported pipeline in YAML.
3. Read data from the local filesystem or a supported SQL source.
4. Apply the documented set of built-in transformations.
5. Write to a local file or supported SQL sink.
6. Run the pipeline through the CLI.
7. Diagnose failures using documented errors and logs.

The stable API, supported Python versions, supported input/output formats, configuration schema, CLI contract, and compatibility policy must be documented. Breaking changes to the public API after `1.0.0` should follow the project's published versioning policy.

## Potential post-1.0 expansions (not commitments)

The initial stable release intentionally focuses on config-driven execution of pipelines using local files and SQL. Additional integrations and capabilities may be considered after `1.0.0`, based on use cases, maintenance cost, compatibility with the existing architecture, and available development effort.

Potential areas for future review include, but are not limited to:

- Remote and distributed storage, including S3 and HDFS.
- Additional database, data-warehouse, and analytical-platform integrations, potentially including Snowflake and Hive.
- Excel and other file formats.
- Generic API source/sink implementations.
- Scheduling, retries, distributed processing, concurrency, and orchestration services.
- Web UI, job queue, monitoring server, and data catalog/lineage systems.
- Expanded custom-component loading or plugin mechanisms.
- Larger processor libraries or a general-purpose expression language.
- Tabular/record conversion utilities (for example, converting `Batch` data to a sequence of row mappings and back), if concrete use cases justify their contracts and maintenance cost.

These examples describe areas that may be evaluated, not features promised for a particular release. After v1.0.0, review candidate enhancements as a separate roadmap decision: identify concrete use cases, define acceptance criteria, estimate implementation and maintenance costs, and determine priority and sequencing. Do not assume that every listed integration will be implemented.

## Release hygiene

Before every public release:

- Run the full test, lint, format, and type-check suites.
- Build the wheel and source distribution.
- Install and smoke-test the built package in a clean environment.
- Review the changelog and release notes.
- Ensure the version in package metadata matches the Git tag.
- Test publication through TestPyPI when useful, then publish the actual release artifact.

The `etlrelay` distribution has already been published to PyPI; see the [ETLRelay project page](https://pypi.org/project/etlrelay/). Before each release, verify that package metadata, the built wheel and source distribution, the Git tag, and the release notes all identify the intended version. Revisit distribution-name availability only if the project proposes changing its published package name.

## Summary roadmap

| Version | Status | Milestone | Release outcome |
|---|---|---|---|
| `0.1.0` | Released | Experimental local CSV pipeline | Initial local CSV pipeline published |
| `0.1.x` | Released | Stabilization | Compatible fixes and documentation improvements |
| `0.2.0` | Released | Batch contract and processors | Basic useful transformations |
| `0.3.0` | Released | Parquet | CSV and Parquet through shared reader/writer interfaces |
| `0.4.0` | Released | Storage contract stabilization | Documented and tested local filesystem behavior; no remote-storage implementation |
| `0.5.0` | Released | SQL source/sink | Tested SQLite reads/writes and mixed file/SQL pipelines |
| `0.6.0` | Released | YAML configuration | Versioned schema validation, explicit component catalog, SQL preflight, and runtime pipeline construction |
| `0.7.0` | Released | CLI | Validate and run pipelines from a shell |
| `0.8.0` | Released | Security and operational readiness | Hardened controls, controlled diagnostics, cleanup, dependency/package checks, and installed-wheel compatibility verification |
| `0.9.0` | In progress | Feature-complete beta | Feature freeze, reader/writer naming cleanup, and full API/representation-contract review |
| `1.0.0rc1` | Planned | Release candidate | Final validation and feedback |
| `1.0.0` | Planned | Stable release | Documented, usable, tested config-driven ETL product |

The version numbers and ordering can be adjusted if implementation reveals a dependency or real user requirement that changes priorities. Keep the principle constant: each release should deliver a coherent, tested increment, and the `1.0.0` milestone should mark API stability rather than feature abundance.
