# v1.0 Feature Scope and Support Policy

This document defines ETLRelay v1.0.0 support and the feature boundary verified during v0.9.0.

The v1.0.0 release retains the reviewed v0.9.0 runtime feature set. See the
[compatibility policy](../compatibility.md) for the stable contract and the
[v1.0.0 readiness record](release-v1.0.0.md) for final verification/publication gates.
External beta feedback is optional and does not block release.

## Feature Freeze

The v1.0 feature set is frozen.

Changes during v1.0.0 release preparation must address:

- Correctness.
- Security.
- Compatibility within the declared support matrix.
- Public API clarity and consistency.
- Testing, documentation, packaging, or release readiness.

New formats, storage backends, processors, integrations, and execution models are deferred.

Any exception must identify a concrete requirement that prevents the agreed v1.0 feature set from working correctly. Record its justification, acceptance criteria, and affected ticket before implementation.

## Feature Inventory

Status meanings:

- **Implemented:** Available in v0.9.0 and covered by the completed reviews/tests.
- **Required but incomplete:** An identified release-blocking feature or correction; none remains in this inventory.
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
| Packaging and compatibility checks | Implemented | Distribution checks and independent wheel/sdist CI smoke tests |
| Tabular protocol naming cleanup | Implemented | `TabularReader`/`TabularWriter` consistently used; no legacy class aliases |
| Public API and contract review | Implemented | Completed review outcomes and corrections in the API review record |
| Final pipeline and failure verification | Implemented | Completed coverage/failure matrices and regression tests |
| Final installation verification | Implemented | Both-artifact verification across the declared support matrix |
| Documentation and beta review | Implemented | Complete references, migration notes, release notes, limitations, and feedback process |
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
| Ubuntu | 3.12 | Full test suite, coverage, quality checks, documentation build, distribution checks, and installed wheel/sdist verification |
| Ubuntu | 3.13 | Installed wheel/sdist compatibility smoke tests |
| Ubuntu | 3.14 | Installed wheel/sdist compatibility smoke tests |
| macOS | 3.12 | Installed wheel/sdist compatibility smoke tests |
| Windows | 3.12 | Installed wheel/sdist compatibility smoke tests |

The compatibility smoke test installs the wheel and source distribution separately and verifies isolated installation, public imports, dependency consistency, direct CSV/Parquet/SQLite composition, CLI help/version, YAML validation, and a minimal CSV CLI pipeline.

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

The required implementation and review work is complete. No unresolved product
release blocker was identified in the final review. The
[beta readiness record](beta-readiness.md) maps tickets 0.9.0-01 through 0.9.0-08
to evidence and classifies remaining work. `RELEASE_CHECKS.md` tracks verification
of the integrated release commit and publication separately; those operational
gates must pass before promotion. A newly reported correctness, security, or
supported-environment regression remains a required fix under the feature freeze.

## Completion Rule

v1.0.0 is ready when its supported contract and compatibility policy are documented, release-blocking defects are resolved, and the final release checks pass across the declared support matrix. Publication follows the existing workflow.

Deferred capabilities do not block v0.9.0, a release candidate, or v1.0.0.
