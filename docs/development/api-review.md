# v0.9.0 Public API Review

## Baseline and outcome

Reviewed the `dev` baseline at commit
`869a5b1ef62d66cdfdeff236db3cd5355d9f0e82` against the
[v1.0 feature scope](v1-scope.md). This record describes the corrections in
this working change; it does not imply that they have been merged or released.

The baseline passed 693 tests with 100% configured branch coverage on Linux /
CPython 3.12.14. Its strict documentation build failed because the API reference
still requested the removed `Reader` class.

No new source, sink, processor, storage backend, configuration schema version,
or CLI command is required by this review.

## Review outcomes

| Area | Outcome | Decision and evidence |
| --- | --- | --- |
| Public names, imports, constructors, and exports | Corrected | Use `TabularReader`/`TabularWriter`; update current examples, diagrams, source docstrings, and generated API targets. Preserve existing constructor arguments. See `core/__init__.py`, package `__init__.py` files, and the API reference. |
| `Batch` and output schema | Accepted | `Batch(table: pa.Table)` retains the supplied Arrow table. Pipeline output compatibility requires matching names, order, types, and nullability; schema/field metadata is ignored. The first processed output batch, including a zero-row batch, establishes the run schema. See `tests/unit/core/test_batch.py` and `tests/unit/pipeline/test_pipeline.py`. |
| Processors and predicates | Corrected | Retain existing signatures and the six comparison operators. Normalize ambiguous selection to `ValueError`; enforce unique final rename names even for duplicate input fields. Existing and new tests are in `tests/unit/processors/`. |
| File composition and storage | Accepted | `FileSource(path, storage, reader)` and `FileSink(path, storage, writer)` own opened streams, borrow component instances, and propagate errors. Local writes truncate and may leave partial output. See unit source/sink/storage tests and file round-trip integration tests. |
| Tabular streams and document parsing | Corrected | Keep separate batch and mapping contracts. Document `YamlDocumentError` as the expected root-shape failure and verify a non-YAML `KeyValueReader` with the real configuration validator. See reader/writer unit tests and `tests/unit/config/test_loader.py`. |
| SQL queries and parameters | Accepted | Retain `SqlSource(engine, query, *, parameters=None)`; bind query values with SQLAlchemy. SQL text and identifiers remain trusted application configuration, not an authorization boundary. Results are materialized into one batch; empty results produce no batches. See unit/integration SQL source tests. |
| SQL writes and transactions | Accepted | Retain `SqlSink(engine, table_name, *, schema=None)`. Append to existing tables; skip zero-row batches before reflection/validation; use one transaction per nonempty batch. Earlier commits survive later failures. See unit/integration SQL sink tests and SQL round-trip tests. |
| SQL resource documentation | Corrected | Replace the copied file-sink note in `SqlSource.read()` with result/connection ownership, eager materialization, and Arrow conversion behavior. |
| YAML schema and registration | Accepted | Retain schema version 1, required root fields, strict built-in properties, explicit registrations, aggregated configuration errors, and builder preflight before runtime factories. Direct builders/factories require validated configuration. See config unit tests, default-component integration tests, and configuration-preflight integration tests. |
| CLI commands, help, and validation | Corrected | Preserve commands, help, logging controls, and exit codes. Correct README claims: `validate` parses and validates without constructing runtime components or resolving SQL environment values. Regression coverage uses an unset SQL reference and forbids builder construction. |
| CLI document errors | Corrected | Empty YAML, non-mapping roots, and non-string root keys return code 3 for both `validate` and `run`, without document contents or a traceback. Previously they returned code 1. See `tests/unit/test_cli_validate.py`. |
| Exceptions, logging, and failure propagation | Accepted with documented correction | Preserve native library exceptions and existing pipeline execution/cleanup precedence. Add only the specific `YamlDocumentError` subtype required to identify expected document failures at the CLI boundary. Existing CLI, pipeline, and SQL engine factory tests cover safe diagnostics and cleanup precedence. |
| Additional formats, backends, write modes, plugins, and conversion APIs | Explicitly deferred | No change to the frozen feature boundary. `KeyValueWriter` and generic record conversion remain deferred. |

## Public imports and compatibility

The supported convenience imports are the responsibility-level packages:

| Package | Public names |
| --- | --- |
| `etlrelay.core` | `Batch`, `Source`, `Processor`, `Sink`, `TabularReader`, `TabularWriter`, `KeyValueReader`, `WriterError` |
| `etlrelay.pipeline` | `Pipeline` |
| `etlrelay.processors` | `SelectColumns`, `RenameColumns`, `FilterRows` |
| `etlrelay.readers` | `CsvReader`, `ParquetReader`, `YamlReader`, `YamlDocumentError` |
| `etlrelay.writers` | `CsvWriter`, `ParquetWriter` |
| `etlrelay.sources` | `FileSource`, `SqlSource` |
| `etlrelay.sinks` | `FileSink`, `SqlSink` |
| `etlrelay.storage` | `FileSystem`, `FileSystemError`, `LocalFileSystem` |
| `etlrelay.security` | `PathValidator`, `PathValidationError` |

The root `etlrelay` package does not provide an umbrella re-export API.
Configuration services and registries use the documented implementation-module
imports, as shown by the generated API reference.

The old `Reader` and `Writer` class names are removed without aliases. Their
modules remain `etlrelay.core.reader` and `etlrelay.core.writer` to avoid an
additional import-path break. `KeyValueReader` remains in the reader module.
This explicitly revises the earlier module-renaming plan and corrects the
changelog's inaccurate claim that those modules were removed.

`ReaderError` remains importable from `etlrelay.core.reader`; it is not a
promise that every reader normalizes failures to that exception. `WriterError`
is used by the Parquet writer for empty iterables and incompatible schemas.

Protocols use structural typing. Runtime `isinstance` checks on protocols only
check member availability; they do not prove return types, stream ownership,
or behavioral substitutability. Both reader protocols contain `read`, so they
must not be distinguished solely through runtime protocol checks.

## Contract details retained for v1.0

- Type annotations define expected Python inputs. This review does not add
  blanket runtime type validation or widen constructor signatures.
- `Batch` can contain duplicate Arrow field names. Selection requires requested
  names to be unambiguous, filtering requires its target to be unambiguous,
  renaming requires unique final names, and SQL boundaries reject duplicates.
- Processors preserve the relevant field types and nullability. `FilterRows`
  uses Arrow comparisons without custom casting and excludes false/null results.
  YAML filter values remain restricted to strings, integers, floats, and booleans;
  SQL bound parameters additionally accept null. Direct Python values follow
  Arrow's comparison support and are not constrained by the YAML schema.
- Output schema enforcement belongs to `Pipeline`; direct writers and sinks
  retain their own format/database checks. There is no implicit reconciliation.
- Tabular readers/writers borrow streams. Callers keep streams open while
  consuming lazy input. File components own and close streams they open.
- An entirely empty pipeline source leaves its sink untouched. Direct calls to
  a file sink still open/truncate its destination, even with no batches.
- CSV writing of no batches writes no bytes. Parquet writing requires at least
  one batch to establish its schema. A zero-row batch with a schema is valid.
- SQL result/connection lifetimes end before Arrow conversion. Sources materialize
  all result rows, so batch-oriented execution does not guarantee bounded memory.
- Direct SQL components borrow caller-owned engines. Configuration-built engines
  belong to the shared engine factory and are released through builder cleanup.
- File writes are not atomic. SQL batch transactions do not provide pipeline-wide
  rollback or automatic retry/idempotency.
- `validate` reads the configuration file and checks document/schema rules.
  `run` additionally resolves component registrations, preflights SQL environment
  references, builds components, executes, and closes builder resources.
- CLI exit codes remain 0 success, 1 unexpected internal error, 2 usage error,
  3 configuration/build failure, and 4 execution/cleanup failure.
- Library errors may include native third-party details. CLI execution diagnostics
  omit underlying messages; controlled logs do not establish universal redaction.

## Exception boundary correction

`YamlDocumentError` subclasses `ValueError`, preserving existing library catches
for YAML root-shape errors. Syntax, duplicate-key, and multiple-document errors
remain `yaml.YAMLError`. `ConfigLoader` continues to propagate reader errors.

The CLI catches the specific document error and emits a controlled shape
message. It does not classify every `ValueError` as user configuration failure;
unrelated internal errors retain exit code 1.

## Follow-up and release blockers

The defects identified in this review are addressed in this change. There is
no additional unresolved runtime API blocker identified by the reviewed evidence.
These corrections must be integrated and required checks must pass before
this ticket is closed.

The following release-readiness gates remain owned by later tickets:

| Ticket | Required follow-up |
| --- | --- |
| 0.9.0-04 | Audit representative supported pipeline combinations and interface boundaries. |
| 0.9.0-05 | Complete the failure/cleanup matrix, including borrowed-stream failure paths and inaccessible resources. |
| 0.9.0-06 | Verify wheel and source-distribution installation and the declared Python/platform matrix. Local Linux/3.12 results do not replace those checks. |
| 0.9.0-07 | Complete examples and user documentation, versioned release links, contribution instructions, and release notes. |
| 0.9.0-08 | Review actual issue-tracker defects and complete beta release sign-off. This source review does not establish that the tracker has no blockers. |

## Validation of this change

Verified locally on Linux / CPython 3.12.14 using the locked dependencies:

- Full unit, integration, and functional suite: **708 passed**.
- Configured statement/branch coverage: **100%**.
- Ruff lint and formatting checks: passed.
- Pyright: zero errors and warnings.
- Strict MkDocs build: passed.
- `git diff --check`: passed.

The 15 additional cases include invalid document shapes through both CLI
commands, preservation of unrelated internal `ValueError` classification,
duplicate-column behavior, non-YAML reader substitution, and validation without
SQL preflight. Twelve new regression cases were demonstrated failing before
implementation corrections.

These results do not certify other Python/platform combinations or complete
later compatibility, failure-matrix, documentation, or beta-sign-off tickets.
