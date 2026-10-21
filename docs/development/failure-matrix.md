# v0.9.0 Failure and Cleanup Matrix

Ticket: **0.9.0-05 — Complete failure, edge-case, and cleanup coverage**.
Reviewed baseline: `dev` commit `31541b9`.

This audit covers the [frozen feature scope](v1-scope.md): local CSV/Parquet,
SQLite, built-in processors, YAML, and the CLI. It reuses existing coverage and
adds targeted cases where behavior or ownership lacked direct evidence.
Successful pipeline combinations are recorded in the
[pipeline coverage matrix](pipeline-coverage.md).

All test paths below are relative to `tests/`. File names identify the focused
suite; specific test names identify important additions or cross-component cases.

## Matrix

| Condition | Expected behavior | Automated evidence |
| --- | --- | --- |
| Entirely empty source | No processors/sink calls; existing destination preserved | `unit/pipeline/test_pipeline.py`: `test_pipeline_handles_empty_source`, `test_empty_pipeline_preserves_existing_file`; `functional/test_sql_pipeline.py` |
| Zero-row batch | Process and validate its schema; CSV writes a header, Parquet writes an empty file, SQL skips inserts/reflection/transactions | `unit/pipeline/test_pipeline.py`, `unit/writers/test_csv.py`, `unit/writers/test_parquet.py`, `unit/sinks/test_sql.py`; `functional/test_sql_pipeline.py` |
| Cross-batch schema mismatch | Reject changed names/order/types/nullability before yielding that batch; zero rows also participate | `unit/pipeline/test_pipeline.py`: `test_rejects_incompatible_output_schema_before_sink_write`, `test_rejects_incompatible_schema_on_zero_row_batch`, `test_zero_row_first_batch_establishes_output_schema` |
| Metadata-only schema difference | Accept compatible fields despite schema/field metadata differences | `unit/pipeline/test_pipeline.py`, `unit/writers/test_parquet.py`: metadata-difference cases |
| Empty or malformed CSV bytes | Zero-byte input and malformed rows raise Arrow errors; borrowed input remains open. Header-only CSV yields no batches | `unit/readers/test_csv.py`: `test_reader_raises_error_for_malformed_csv`, `test_reader_handles_csv_with_header_and_no_rows` |
| Malformed Parquet | Raise Arrow error and leave the borrowed input open | `unit/readers/test_parquet.py`: `test_reader_raises_arrow_error_for_malformed_parquet` |
| Malformed/unsafe YAML | Reject syntax, duplicate/unhashable keys, multiple documents, and unsafe tags; preserve borrowed-stream ownership | `unit/readers/test_yaml.py`; CLI syntax tests in `unit/test_cli_validate.py` and `functional/test_cli_installed.py` |
| Invalid YAML root shape | Reject empty/non-mapping/non-string-key roots; CLI returns 3 without document values | `unit/readers/test_yaml.py`; `unit/test_cli_validate.py`: `test_invalid_document_shape_is_a_safe_configuration_failure` |
| Invalid schema/components or missing SQL references | Reject before runtime factories or data I/O; controlled errors omit resolved connection values | `integration/test_configuration_preflight.py`, `unit/config/test_pipeline_builder.py`, `unit/config/test_sql_engine_factory.py` |
| Missing paths, traversal, symlink escape | Missing input becomes `FileSystemError`; containment failures reject before opening; outside contents unchanged | `unit/storage/test_local.py`, `unit/security/test_path.py` |
| Inaccessible resources or I/O failure | Preserve permission/I/O exceptions at the storage layer; CLI emits controlled failures | `unit/storage/test_local.py::TestLocalFileSystemErrorPropagation`; `unit/test_cli_validate.py`, `unit/test_cli_run.py` |
| SQL engine creation failure | Controlled factory error without resolved URL/driver message | `unit/config/test_sql_engine_factory.py`: creation-error and credential-log tests |
| SQL connection acquisition failure | Native error propagates to library caller; borrowed engine is not disposed. CLI returns 4 and closes builder resources without exposing credentials | `unit/sources/test_sql.py`: `test_connection_failure_propagates_without_disposing_borrowed_engine`; `unit/test_cli_run.py`: `test_sql_connection_failure_is_safe_and_closes_builder` (source and sink) |
| Invalid SQL syntax | Raise native database error and return the acquired connection to its pool; no query payload in ETLRelay logs | `integration/sources/test_sql.py`: `test_malformed_sql_returns_connection_to_pool_without_logging_query` |
| SQL execution, duplicate result names, or fetch iteration failure | Close result and connection when acquired; preserve borrowed engine | `unit/sources/test_sql.py`; `unit/sinks/test_sql.py`: `test_sql_source_closes_result_and_connection_when_iteration_fails` |
| SQL-to-Arrow conversion failure | Result and connection have already been closed before conversion is attempted | `unit/sources/test_sql.py`: `test_arrow_conversion_failure_occurs_after_sql_resources_are_closed` |
| Processor failure before/after first output | Close active input. Before the first processed batch, preserve the destination; during writing, close output and retain the serialized prefix | `unit/pipeline/test_pipeline.py`: `test_processor_failure_closes_streams_and_preserves_output_prefix` (CSV/Parquet, first/second batch) |
| Sink failure and partial file writes | Propagate writer/storage failure, close owned output, retain empty/partial output rather than restoring previous contents | `unit/sinks/test_file.py`; `unit/pipeline/test_pipeline.py`: `test_schema_failure_preserves_partially_written_file` |
| Borrowed writer stream after I/O or upstream failure | Preserve exception identity and leave the supplied stream open; a successfully finalized prefix remains readable | `unit/writers/test_csv.py`, `unit/writers/test_parquet.py`; `unit/writers/test_iteration_failures.py` |
| Parquet finalization failure | Preserve an existing upstream/serialization error over footer failure; otherwise propagate footer failure; secondary logs omit exception messages | `unit/writers/test_parquet.py`: `test_parquet_writer_handles_footer_failure_without_masking_primary_error` |
| SQL failed batch or later-batch failure | Roll back the failed batch; preserve prior commits; release transaction resources | `integration/sinks/test_sql.py`: `test_failed_batch_rolls_back_all_rows`, `test_previous_batch_commit_survives_later_batch_failure`, `test_sql_sink_rolls_back_failed_batch_but_preserves_prior_commit`; unit transaction-context tests |
| Early sink return or pipeline iterator cleanup failure | Close active iterators; execution failure takes precedence; first cleanup-only failure propagates; attempt remaining cleanup | `unit/pipeline/test_pipeline.py`: early-stop and iterator-cleanup tests |
| Builder/factory cleanup after success or failure | Dispose owned engines, attempt all disposals, keep cleanup idempotent, preserve primary build/execution failure | `unit/config/test_sql_engine_factory.py`, `unit/config/test_pipeline_builder.py`, `unit/test_cli_run.py` |
| Secret redaction at user-facing boundaries | Tested connection/password/query/record sentinels absent from controlled CLI output and ETLRelay logs | `unit/test_cli.py`, `unit/test_cli_run.py`, `functional/test_cli_installed.py`, SQL engine factory tests, and the new Parquet secondary-cleanup test |

## Defect found and corrected

Previously, the native Parquet writer's context-manager exit could replace an
upstream processing error with an error writing the footer. A regression test
reproduced this against a real PyArrow writer and a deterministic failing stream.

`ParquetWriter` now explicitly attempts finalization after failure, retains the
original exception, and logs a secondary finalization error using its type only.
A finalization error after otherwise successful serialization still propagates.
There is no public signature, configuration-schema, or CLI exit-code change.

This does not make file output atomic. A failed footer may leave unreadable
output. Successfully finalized earlier batches may remain readable after an
upstream failure; they are still partial results from a failed run.

## Test design and limits

- Permission failures use patched file opening rather than chmod assumptions;
  behavior stays deterministic under privileged users and across platforms.
- Connection refusal uses SQLAlchemy engine doubles rather than external
  services. Actual SQLite syntax and transaction failures use local databases.
- The processor/output test uses a two-batch reader double and real CSV/Parquet
  serialization, retaining stream references so garbage collection cannot hide
  missing cleanup.
- Normal-path stream, SQL result/connection, and engine cleanup tests remain in
  place. New assertions supplement those existing tests rather than duplicating
  a complete source/sink combination matrix.
- Redaction evidence concerns ETLRelay-controlled diagnostics. Native library
  exceptions can contain sensitive data; arbitrary third-party exceptions,
  application handlers, filenames, and configuration keys are not universally
  sanitized. Test sentinels do not establish universal sanitization.
- Resource release means closure/disposal is attempted at the owning boundary.
  A failing underlying close/dispose operation cannot be guaranteed to release
  an external resource. The tested contracts establish exception precedence and
  continued cleanup attempts where documented.

The Parquet precedence defect is addressed in this change. No other unresolved
release-blocking defect was identified by this audit. Required CI and integration
into `dev` remain prerequisites for closing the ticket. Supported-platform
installation verification remains assigned to 0.9.0-06.

## Verification and acceptance

Verified locally on Linux / CPython 3.12.14 using locked dependencies:

- Full unit, integration, and functional suite: **725 passed**.
- Configured statement/branch coverage: **100%**.
- Ruff lint and formatting checks: passed.
- Pyright: zero errors and warnings.
- Strict MkDocs build and `git diff --check`: passed.

The change adds 15 test cases and strengthens existing failure assertions.
The primary-error/footer-error regression was demonstrated failing before the
Parquet writer correction.

- [x] Failure categories and expected behavior map to automated evidence.
- [x] Applicable categories have meaningful unit, integration, or functional coverage.
- [x] Normal and relevant failure-path resource ownership is verified.
- [x] Tested secrets are absent from controlled CLI output and logs.
- [x] Propagation, transaction boundaries, and partial outputs match the documented contracts.
- [x] The release-blocking defect found by this audit is fixed and regression-tested.

These are local results for this change, not certification of the full supported
platform matrix or confirmation that the patch has been merged.
