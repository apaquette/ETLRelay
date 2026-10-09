# ETLRelay Roadmap: `0.1.0` to `1.0.0`

## Purpose

This roadmap defines incremental, testable milestones from the current local-file pipeline implementation to a stable ETLRelay `1.0.0` release.

The target for `1.0.0` is a lightweight, synchronous, batch-oriented ETL framework that can read from local files or SQL, apply a small set of transformations, and write to local files or SQL. File storage and serialization remain separate concerns. YAML configuration and a small CLI make pipelines usable without writing Python for every job.

The roadmap is feature-led, not date-led. A version should be released when its acceptance criteria are met; the version numbers are proposed milestones, not a promise to publish every milestone on a fixed schedule.

## Versioning policy

ETLRelay is in initial development, so `0.y.z` is appropriate while the public API is still evolving. Semantic Versioning explicitly says that a `0.y.z` public API should not yet be considered stable and recommends `0.1.0` as a reasonable starting point. See [Semantic Versioning 2.0.0](https://semver.org/) and the [Python Packaging User Guide's versioning discussion](https://packaging.python.org/en/latest/discussions/versioning/).

Until `1.0.0`:

- Use a **patch release** such as `0.1.1` for compatible fixes to a published release.
- Use a **minor release** such as `0.2.0` for a coherent feature milestone. Public APIs may still evolve before `1.0.0`, but document notable breaking changes.
- Never replace or modify an already-published release. Publish a new version instead.
- Use a release candidate such as `1.0.0rc1` only when the intended `1.0.0` feature set is complete and the remaining work is validation and defect correction.

## Current state and first release

### `0.1.0` — Experimental local CSV pipeline

**Goal:** Publish the first usable development release of the current implementation, once release checks are green.

Expected scope:

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

This is an experimental release, not a promise of API stability. The `0.1.0` milestone is complete when a real local CSV input can pass through a pipeline and be written to a real CSV output, the edge cases covered by the tests are settled, and the package can be built and installed outside the development checkout.

**Release gate:**

- [ ] Full test suite passes.
- [ ] Ruff lint and format checks pass.
- [ ] Pyright passes at the project's configured level.
- [ ] A source distribution and wheel build successfully.
- [ ] Install the built wheel in a clean environment and run a small import/usage smoke test.
- [ ] README contains accurate installation instructions and one working example.
- [ ] Project metadata, licence, package contents, and supported Python version are correct.
- [ ] Release notes explain that the API may change before `1.0.0`.
- [ ] Create a Git tag for the release and retain the built artifacts.

Recommended build check: `uv build`. The Python Packaging User Guide describes building source and wheel distributions and supports using TestPyPI to rehearse a publication before the real release: [Building and Publishing](https://packaging.python.org/en/latest/guides/section-build-and-publish/).

### `0.1.x` — Stabilize the first release

**Goal:** Correct defects found during initial use without expanding the feature set unnecessarily.

Scope:

- Fix defects in the pipeline, batch, path validation, local storage, CSV reading, or CSV writing.
- Improve error messages where they currently obscure the failing operation.
- Correct packaging, installation, documentation, and typing issues.

Do not use patch releases to sneak in unrelated, large features.

## Feature roadmap

### `0.2.0` — Batch contract and built-in processors

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

### `0.3.0` — Parquet format support

**Goal:** Support a second high-value tabular format while retaining the format/storage boundary.

Scope:

- Implement `ParquetReader` and `ParquetWriter` against the existing stream-based reader/writer protocols where the chosen Arrow APIs support that contract.
- Test schema and type preservation, empty data, malformed input, and round trips.
- Verify that the same reader/writer components work with `LocalFileSystem` without special cases in `FileSource` or `FileSink`.
- Document CSV and Parquet behavior, including limitations and format-specific differences.

**Done when:** Local CSV and Parquet sources/sinks work through the same file composition model.

### `0.4.0` — Storage compatibility and optional S3 backend

**Goal:** Validate that `FileSystem` is a useful substitution boundary, not just an abstraction used by one implementation.

First, stabilize and test the `FileSystem` contract around stream lifetime, read/write modes, error propagation, path handling, and output overwrite semantics.

**Conditional feature:** Add an `S3Storage` implementation if S3 is a real target for the first stable release. It should:

- implement the existing `FileSystem` contract without CSV/Parquet-specific logic;
- use standard credential-provider mechanisms or environment-based configuration rather than embedding secrets in pipeline definitions;
- have unit tests using suitable doubles and optional, separately marked integration tests;
- document object key, overwrite, stream, and error semantics.

S3 is a useful v1.0 candidate, but it is not a hard v1.0 gate unless there is a concrete requirement for it. If there is no such requirement, defer S3 rather than inventing a use case solely to validate the abstraction. HDFS remains post-1.0 unless requirements change.

### `0.5.0` — SQL source and sink

**Goal:** Add database input/output through SQLAlchemy without forcing SQL into the file storage or reader/writer abstractions.

Scope:

- Implement `SqlSource` and `SqlSink` as independent `Source`/`Sink` implementations.
- Use SQLAlchemy connection/statement facilities.
- Define the initial database support and test at least SQLite for repeatable integration tests.
- Support parameterized query values.
- Validate or safely construct SQL identifiers that cannot be supplied as bind parameters.
- Support a small, documented write mode, initially `append` and optionally `replace` if semantics are clear.
- Convert query results and input batches to/from the agreed Arrow-backed `Batch` contract.
- Test transaction and error behavior.

**Done when:** A SQL query can supply batches to a pipeline, and processed batches can be written to a SQL table with safe parameter handling and documented transaction behavior.

### `0.6.0` — Declarative YAML configuration

**Goal:** Let users define supported pipelines without writing Python assembly code.

Scope:

- Define and document a versioned YAML schema for source, processor sequence, and sink.
- Validate required properties and types before execution.
- Resolve only explicitly supported component types through a small, explicit mapping.
- Support configured storage and file formats where implemented.
- Reference secrets through environment variables or another clearly documented mechanism; do not accept plaintext secrets as the recommended approach.
- Reject unknown component types, unknown properties where appropriate, invalid combinations, and malformed configuration with actionable errors.
- Do not use `eval`, arbitrary imports, or unrestricted Python execution to construct pipelines.

**Done when:** YAML configuration builds the same pipeline as direct Python composition and invalid configuration is rejected before the pipeline starts.

### `0.7.0` — Command-line interface

**Goal:** Make the framework practical to run from a shell or automation script.

Initial commands:

- `etlrelay run pipeline.yaml`
- `etlrelay validate pipeline.yaml`
- `etlrelay version`

Scope:

- Define useful process exit codes.
- Print actionable validation and execution errors.
- Keep secrets and sensitive payloads out of terminal output.
- Keep the CLI thin; pipeline construction and execution logic belong in the underlying library.
- Test commands without requiring external databases or cloud resources for the unit suite.

**Done when:** A user can validate and run a supported YAML pipeline through the installed CLI.

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
- Test full pipelines across supported combinations: local CSV, local Parquet, SQL input/output, and S3 only if it has been included in the supported feature set.
- Test empty inputs, empty batches, schema mismatches, malformed data, inaccessible resources, processor failures, sink failures, and stream cleanup.
- Test a clean install on each supported Python version/platform combination the project claims to support.
- Complete README, quick start, examples, API reference, configuration reference, security notes, contribution instructions, and release notes.
- Document unsupported features and known limitations.

**Done when:** No required v1.0 feature remains unimplemented, release-blocking defects are resolved, and the project can maintain a clear public API contract.

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

## Explicitly post-1.0 unless requirements change

- HDFS support.
- Excel support.
- Generic API source/sink framework.
- Scheduling and recurring execution.
- Retries, distributed processing, concurrency, and orchestration services.
- Web UI, job queue, monitoring server, and data catalog/lineage system.
- Large plugin registries or dynamic extension frameworks.
- Large processor libraries or a general-purpose expression language.

These are not necessary to establish the initial stable ETL product. Revisit them only when a concrete use case justifies the additional maintenance burden.

## Release hygiene

Before every public release:

- Run the full test, lint, format, and type-check suites.
- Build the wheel and source distribution.
- Install and smoke-test the built package in a clean environment.
- Review the changelog and release notes.
- Ensure the version in package metadata matches the Git tag.
- Test publication through TestPyPI when useful, then publish the actual release artifact.

PyPI distribution names are distinct from import package names and need to be checked before first publication. The exact `etlrelay` project URL did not return a project page in the web check performed for this roadmap, but similarly named projects exist, including [`pyetlrelay`](https://pypi.org/project/pyetlrelay/), [`etlrelay-sdk`](https://pypi.org/project/etlrelay-sdk/), and [`etlrelay-io`](https://pypi.org/project/etlrelay-io/). Confirm the distribution name is available and appropriate immediately before publishing; do not assume it is reserved for this project.

## Summary roadmap

| Version | Milestone | Release outcome |
|---|---|---|
| `0.1.0` | Experimental local CSV pipeline | Current pipeline can be built, installed, tested, and run end to end |
| `0.1.x` | Stabilization | Compatible fixes and documentation improvements |
| `0.2.0` | Batch contract and processors | Basic useful transformations |
| `0.3.0` | Parquet | CSV and Parquet through shared reader/writer interfaces |
| `0.4.0` | Storage compatibility; optional S3 | Validate storage substitution and add S3 only if justified |
| `0.5.0` | SQL source/sink | Tested database input/output |
| `0.6.0` | YAML | Validated declarative pipelines |
| `0.7.0` | CLI | Validate and run pipelines from a shell |
| `0.8.0` | Security and operational readiness | Security review, errors/logging, installation and CI gates |
| `0.9.0` | Feature-complete beta | Feature freeze and full API review |
| `1.0.0rc1` | Release candidate | Final validation and feedback |
| `1.0.0` | Stable release | Documented, usable, tested initial ETL product |

The version numbers and ordering can be adjusted if implementation reveals a dependency or real user requirement that changes priorities. Keep the principle constant: each release should deliver a coherent, tested increment, and the 1.0 milestone should mark API stability rather than feature abundance.
