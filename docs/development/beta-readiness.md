# v0.9.0 Beta Readiness and Feedback

Ticket: **0.9.0-08**, [#139](https://github.com/apaquette/ETLRelay/issues/139).
Review date and target release date: **2026-10-21**.
Integrated baseline: `1b0993b1b5bc012754c5c3960c6b79f21d36f189`.

## Release completion

v0.9.0 was published on 2026-10-21. The completed
[release verification record](release-verification-v0.9.0.md) contains final CI,
TestPyPI, PyPI, GitHub release, and documentation evidence. Tickets #139 and #37
are closed. The preparation review below remains historical evidence; its
then-pending publication gates have been completed.

External beta feedback is optional, and none is claimed to have been collected.
Maintainer verification establishes v1.0.0 readiness without a mandatory waiting
period or RC cycle. See the [stable-release record](release-v1.0.0.md) and
[compatibility policy](../compatibility.md). Future enhancements belong to a
separate post-v1.0 roadmap review.

## Decision

The intended v1.0 feature set is implemented and frozen. Preceding tickets
0.9.0-01 through 0.9.0-07 are closed, their reviews and tests are integrated,
and no unresolved product release blocker was found in the public issue review.
The source is prepared as **v0.9.0 — feature-complete beta**, using the existing
release process. Release-facing documentation describes v0.9.0; it is not a
claim that publication jobs have already run.

The reviewed product is synchronous local CSV/Parquet and SQLite-backed SQL
pipelines, the existing select/rename/filter processors, direct Python
composition, YAML schema version 1, and CLI execution. Mapping-shaped documents
use `KeyValueReader`; tabular protocols use `TabularReader` and `TabularWriter`.
No required runtime feature remains incomplete. A beta milestone does not make
the pre-1.0 public API a stable v1.0 compatibility promise.

## Completed ticket evidence

| Ticket | Outcome and evidence |
| --- | --- |
| [0.9.0-01 / #132](https://github.com/apaquette/ETLRelay/issues/132) | Closed; [frozen inventory and support policy](v1-scope.md) |
| [0.9.0-02 / #133](https://github.com/apaquette/ETLRelay/issues/133) | Closed; [representation contracts](../architecture/data-representation-contracts.md), [stream protocols](../architecture/reader_and_writer.md), and [migration](migration-v0.9.0.md) |
| [0.9.0-03 / #134](https://github.com/apaquette/ETLRelay/issues/134) | Closed; [API review outcomes](api-review.md), focused regression tests, and [public reference](../api-reference.md) |
| [0.9.0-04 / #135](https://github.com/apaquette/ETLRelay/issues/135) | Closed; [pipeline coverage matrix](pipeline-coverage.md), including installed CLI boundaries |
| [0.9.0-05 / #136](https://github.com/apaquette/ETLRelay/issues/136) | Closed; [failure matrix](failure-matrix.md), resource cleanup, redaction, and partial-write regression tests |
| [0.9.0-06 / #137](https://github.com/apaquette/ETLRelay/issues/137) | Closed; [packaging verification](packaging-verification.md), independent wheel/sdist installation, and the five-job CI matrix below |
| [0.9.0-07 / #138](https://github.com/apaquette/ETLRelay/issues/138) | Closed; [documentation review](documentation-review.md), executable examples/quick start, migration, and strict documentation build |
| 0.9.0-08 / #139 | This review, v0.9.0 metadata/lockfile, finalized [release notes](release-notes-v0.9.0.md), release checklist, and feedback process |

## Support verification

The integrated documentation baseline passed
[CI run 39642253494](https://github.com/apaquette/ETLRelay/actions/runs/39642253494).
Each job completed successfully. Both wheel and source distribution are installed
separately outside the checkout; public imports, direct CSV/Parquet/SQLite
pipelines, dependency consistency, and installed CLI/YAML operation are exercised.

| Supported combination | Verification evidence |
| --- | --- |
| Ubuntu / CPython 3.12 | [Full suite, coverage, quality, documentation, distributions, installed artifacts](https://github.com/apaquette/ETLRelay/actions/runs/39642253494/job/119368522094) |
| Ubuntu / CPython 3.13 | [Both-artifact compatibility smoke](https://github.com/apaquette/ETLRelay/actions/runs/39642253494/job/119368991368) |
| Ubuntu / CPython 3.14 | [Both-artifact compatibility smoke](https://github.com/apaquette/ETLRelay/actions/runs/39642253494/job/119368991439) |
| macOS / CPython 3.12 | [Both-artifact compatibility smoke](https://github.com/apaquette/ETLRelay/actions/runs/39642253494/job/119368991380) |
| Windows / CPython 3.12 | [Both-artifact compatibility smoke](https://github.com/apaquette/ETLRelay/actions/runs/39642253494/job/119368991355) |

These are the five declared combinations, not a cross-product of all Python
versions and operating systems. Full tests run on Ubuntu/3.12; the other entries
provide artifact smoke coverage. SQLite is the tested database. Other SQLAlchemy
dialects require drivers and independent verification and are not guaranteed.

The version/lockfile and final release-documentation changes must pass their own
integrated CI run before promotion. The baseline result is supporting evidence,
not a substitute for verification of the release commit. Record its commit and
run URL in `RELEASE_CHECKS.md` when complete.

## Local v0.9.0 verification

The release-preparation checkout passed checks with locked dependencies on Linux
CPython 3.12.14:

- **736 tests passed, 100% configured statement/branch coverage**, including
  installed-example and quick-start execution.
- Lockfile consistency, installed dependency consistency, Ruff lint/format,
  Pyright, strict MkDocs, and diff checks passed.
- Fresh v0.9.0 wheel/sdist builds, Twine metadata/content checks, and isolated
  installation/execution of both artifacts passed.
- The dependency audit exited successfully with **no known vulnerabilities**.
  It also reported archived `verspec`, a transitive documentation dependency of
  `mike`; this is recorded as later tooling-maintenance work below.

Commands are recorded in `RELEASE_CHECKS.md`. Local results do not replace the
macOS/Windows CI checks above or final integrated CI.

## Issue review and remaining work

The public open-issue list was reviewed on 2026-10-21. It contained only the
[parent milestone #37](https://github.com/apaquette/ETLRelay/issues/37) and this
final review ticket #139; neither reported a separate unresolved defect.
All seven prerequisite tickets were confirmed closed. This is a dated review,
not a guarantee against newly reported defects; repeat the check before merge.

| Classification | Remaining work and disposition |
| --- | --- |
| Required release gate | Pass CI for the integrated v0.9.0 commit, record its SHA/run, review any newly opened defects, and complete `RELEASE_CHECKS.md`. Do not promote a failing candidate. |
| Required publication work | Run the existing TestPyPI rehearsal, promote reviewed `dev` to `main`, verify PyPI, generated `v0.9.0` tag/GitHub release and hosted `0.9.0` documentation. These actions have not been performed by this source review. |
| Required fix if discovered | Incorrect data/schema results, resource leaks, credential exposure in controlled diagnostics, supported-environment installation failures, or documented API/CLI regressions block release until fixed and regression-tested. |
| Known limitation | Non-atomic/truncating file writes and partial or unreadable output after failure; SQL append-only output to existing tables and per-batch commits; SQL result materialization; path containment is not a sandbox; no universal third-party exception/log redaction. These remain explicit in [security](../security.md) and [API](api-review.md) references. |
| Later release work | S3/HDFS, additional formats/processors/databases, dynamic plugins, scheduling/retries/distributed execution, SQL creation/upsert/pipeline-wide transactions, mapping-document writing, and generic row-record conversion remain outside the frozen boundary. A feature request does not become a v0.9.0 blocker. |
| Later tooling maintenance | Review `mike`/`verspec` dependency maintenance before future releases. The current audit reports `verspec` archived but no known vulnerability and exits successfully; it is documentation tooling, not a runtime dependency. No dependency-ignore rule or unsupported security claim is introduced. |
| Feedback follow-up | Gather the focused feedback below, correct defects within scope, then perform final v1.0 release-candidate validation. Feedback is not claimed to have been collected by this review. |

## Focused beta feedback

Use the [v0.9.0 quick start](../getting-started.md), maintained
[examples](https://github.com/apaquette/ETLRelay/tree/v0.9.0/examples), and
[migration guide](migration-v0.9.0.md). Check a small representative workflow:

- **Installation:** Does `etlrelay==0.9.0` install in a clean environment on a
  declared combination? Do imports, `etlrelay version`, and help work?
- **Usability:** Can you follow the quick start, validate YAML, execute the job,
  and understand an invalid-configuration diagnostic and exit code?
- **API clarity:** Are tabular batches versus mapping documents, constructor
  arguments, schema rules, stream ownership, and engine cleanup clear?
- **Correctness:** Do output records, types, column order, null behavior, and
  processor ordering match expectations? Are empty inputs and failures
  consistent with documented persistence and cleanup behavior?

Report non-sensitive defects through
[GitHub Issues](https://github.com/apaquette/ETLRelay/issues). Include the package
version, Python/OS, artifact/install method, minimal synthetic input/configuration,
reproduction commands, expected versus actual output, and exit code. Include the
source commit when testing an unpublished archive. Remove credentials, resolved
connection URLs, production records, and sensitive logs before posting.
Report suspected vulnerabilities privately following the
[Security Policy](https://github.com/apaquette/ETLRelay/blob/v0.9.0/SECURITY.md).

For each report, reproduce it and classify it as a required fix, documented known
limitation, or deferred enhancement. A release-blocking defect needs a focused
regression test and a rerun of affected checks; published fixes require a new
version rather than replacing v0.9.0 files. Track enhancements separately without
expanding the beta scope. Do not mark feedback collected until actual reports
or review sessions have been recorded.
