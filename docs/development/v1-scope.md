# v1.0 Feature Scope and Support Policy

This document defines the feature boundary for ETLRelay v0.9.0 and v1.0.0.

The implementation baseline is v0.8.0. An implemented capability remains subject to the API review, regression testing, and release verification required by v0.9.0.

## Feature Freeze

The v1.0 feature set is frozen.

Changes during v0.9.0 and subsequent release-candidate work must address:

- Correctness.
- Security.
- Compatibility within the declared support matrix.
- Public API clarity and consistency.
- Testing, documentation, packaging, or release readiness.

New formats, storage backends, processors, integrations, and execution models are deferred.

Any exception must identify a concrete requirement that prevents the agreed v1.0 feature set from working correctly. Record its justification, acceptance criteria, and affected ticket before implementation.

## Feature Inventory

Status meanings:

- **Implemented:** Available in the v0.8.0 baseline; final review and verification remain required.
- **Required but incomplete:** Necessary work before the v0.9.0 feature-complete criteria can be met.
- **Deferred:** Excluded from v1.0; future consideration is not a commitment.
- **Explicitly unsupported:** Behavior or usage outside the v1.0 contract.

| Capability | Status | Boundary |
| --- | --- | --- |
| Arrow-backed `Batch` | Implemented | Tabular data with documented schema and empty-batch semantics |
| `Source`, `Processor`, `Sink`, and `Pipeline` | Implemented | Synchronous, batch-oriented execution |
| Local filesystem storage | Implemented | Binary streams, path containment, and documented ownership/error behavior |
| CSV reading and writing | Implemented | Through the shared file source/sink composition model |
| Parquet reading and writing | Implemented | Through the shared file source/sink composition model |
| Built-in processors | Implemented | `SelectColumns`, `RenameColumns`, and the existing limited `FilterRows` predicate model |
| SQL source and sink | Implemented | SQLAlchemy query input and append-only output to existing tables |
| YAML configuration | Implemented | Schema version 1, strict validation, explicit registrations, and runtime construction |
| Mapping-document reading | Implemented | Separate `KeyValueReader` contract and safe `YamlReader` implementation |
| CLI | Implemented | `run`, `validate`, `version`, help, and operational logging controls |
| Security and operational controls | Implemented | Existing path checks, preflight, controlled diagnostics, cleanup, and dependency/package checks |
| Packaging and compatibility checks | Implemented | Existing distribution checks and installed-wheel CI smoke tests |
| Tabular protocol naming cleanup | Required but incomplete | Rename `Reader`/`Writer` to `TabularReader`/`TabularWriter` consistently |
| Public API and contract review | Required but incomplete | Names, constructors, signatures, exports, schemas, CLI behavior, and exceptions |
| Final pipeline and failure verification | Required but incomplete | Audit existing tests and close demonstrated gaps |
| Final installation verification | Required but incomplete | Verify release artifacts across the declared support matrix |
| Documentation and beta review | Required but incomplete | Complete documentation, migration notes, limitations, and release readiness |
| S3, HDFS, and other remote storage | Deferred | No remote-storage implementation is required for v1.0 |
| Additional formats and integrations | Deferred | Includes JSON configuration readers, Excel, generic APIs, and additional database-specific integrations |
| Additional processors and expression languages | Deferred | Retain the existing processor set and predicate model |
| `KeyValueWriter` | Deferred | No demonstrated v1.0 use case; do not add solely for symmetry |
| Tabular/row-record conversion utilities | Deferred | Review the representation boundary without adding a generic conversion framework |
| Dynamic plugin loading | Deferred | Existing explicit component registration remains available |
| Scheduling, retries, concurrent/distributed execution, and orchestration services | Deferred | Not required for synchronous pipeline execution |
| SQL replace/upsert modes, table creation, migrations, and ORM-model integration | Explicitly unsupported | SQL output appends to existing compatible tables |
| Pipeline-wide transactions and automatic rollback of previous output | Explicitly unsupported | File writes may be partial; SQL commits occur per nonempty batch |
| Arbitrary code execution from YAML | Explicitly unsupported | No `eval`, arbitrary imports, or import-by-string construction |

Deferred and explicitly unsupported capabilities are excluded from the v0.9.0 completion criteria.

## Python and Platform Support

The supported interpreter family is CPython 3.12, 3.13, and 3.14.

Package metadata declares:

`requires-python = ">=3.12,<3.15"`

Python 3.12 is the default development interpreter and the configured static-analysis target.

The release support matrix is the following set of combinations, rather than every combination of the listed Python versions and operating systems:

| Platform | CPython | Required verification |
| --- | --- | --- |
| Ubuntu | 3.12 | Full test suite, coverage, quality checks, documentation build, distribution checks, and installed-wheel CLI verification |
| Ubuntu | 3.13 | Installed-wheel compatibility smoke test |
| Ubuntu | 3.14 | Installed-wheel compatibility smoke test |
| macOS | 3.12 | Installed-wheel compatibility smoke test |
| Windows | 3.12 | Installed-wheel compatibility smoke test |

The compatibility smoke test verifies isolated installation, package and dependency imports, dependency consistency, CLI help/version, YAML validation, and a minimal CSV pipeline.

Smoke coverage does not imply that the full test suite runs on every matrix entry.

CI uses GitHub-hosted `*-latest` runners. This policy does not promise particular operating-system releases or CPU architectures beyond those actually exercised by the release checks.

Other Python/platform combinations may work but are not release-supported or independently verified. Other Python implementations and Python versions outside the declared range are not supported.

The matrix records required checks. Successful release verification must be established from actual CI results.

## Storage, Format, and Database Support

| Area | v1.0 support |
| --- | --- |
| File storage | `LocalFileSystem` |
| Tabular file input/output | CSV and Parquet |
| Configuration documents | Mapping-shaped YAML using schema version 1 |
| SQL reference backend | SQLite through SQLAlchemy |
| Other SQLAlchemy dialects | Unverified compatibility; not guaranteed support |

Other SQLAlchemy dialects require appropriate drivers and independent verification of queries, identifiers, type conversion, reflection, transactions, and cleanup. SQLAlchemy compatibility alone does not establish ETLRelay support for a database.

SQLite is the required database backend for repeatable automated integration and functional tests. External database services are not required for v1.0 release verification.

## Operational Boundaries

- Execution is synchronous and batch-oriented.
- Processors run in their configured order.
- Output schema compatibility is enforced during execution.
- Entirely empty sources do not invoke the sink.
- Zero-row batches still participate in processing and schema validation.
- File sources/sinks own streams they open; readers/writers borrow supplied streams.
- Pipeline execution attempts to close active iterators exposing callable `close()` methods.
- Local output writes are not atomic and may truncate existing files or leave partial output.
- SQL sinks append using one transaction per nonempty batch; earlier commits survive later failures.
- Direct Python SQL callers own their engines. Configuration-built engines follow the builder's documented lifecycle.
- Path containment is not a complete filesystem sandbox.
- ETLRelay-controlled diagnostics have documented protections; arbitrary third-party exceptions and application logging are not guaranteed to be sanitized.

Mapping-shaped documents are distinct from sequences of row records. `KeyValueReader` remains separate from the tabular reader/writer protocols.

## Required Work and Release Blockers

These are required work items, not claims that every review area contains a defect.

| Requirement | Owning ticket | Completion evidence |
| --- | --- | --- |
| Rename tabular protocols and review mapping-document separation | 0.9.0-02 | Consistent implementation, exports, annotations, tests, examples, documentation, and migration decision |
| Confirm `ConfigLoader` depends on `KeyValueReader` | 0.9.0-02 | Implementation review and a test using an alternative protocol implementation |
| Record writer/conversion deferral decisions | 0.9.0-02 | Representation-contract documentation agrees with this scope |
| Review remaining public API and behavior | 0.9.0-03 | Recorded review outcomes and regression tests for justified changes |
| Resolve conflicting descriptions of CLI `validate` | 0.9.0-03 | Implementation and tests establish whether it constructs runtime components or performs builder preflight |
| Verify representative supported pipelines | 0.9.0-04 | Coverage matrix linked to passing integration/functional tests |
| Verify failures, cleanup, redaction, and partial writes | 0.9.0-05 | Failure matrix linked to passing tests |
| Verify clean installation and declared environments | 0.9.0-06 | Built-artifact installation results and successful matrix checks |
| Complete documentation and correct stale claims | 0.9.0-07 | Accurate documentation, working examples, and strict documentation build |
| Resolve release-blocking defects and prepare beta | 0.9.0-08 | Completed release review and release checklist |

The existing CI builds and inspects the source distribution but the supplied workflow explicitly installs only the wheel. Ticket 0.9.0-06 must verify installation from the source distribution as well.

No additional runtime feature gap is established by the files reviewed for this scope record. Later implementation review or testing may identify defects; track them under the owning ticket without expanding the feature boundary.

## Completion Rule

v0.9.0 is feature-complete when all required work above is finished, release-blocking defects are resolved, and support claims match verification evidence.

Deferred capabilities do not block v0.9.0, a release candidate, or v1.0.0.