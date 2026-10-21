# v0.9.0 Pipeline Coverage

Ticket: **0.9.0-04 — Complete representative pipeline coverage**.
Baseline: `dev` commit `3f88414`.

The [frozen scope](v1-scope.md) includes local CSV, local Parquet, and
SQLAlchemy/SQLite. S3 and other remote storage are deferred and are not required
by this matrix. Other SQLAlchemy dialects are not verified by these tests.

## Source/sink matrix

The existing parametrized integration test
`tests/integration/test_configured_pipeline_combinations.py::test_supported_source_sink_combination_runs_end_to_end`
loads real YAML, validates it with the default catalog, builds a pipeline,
executes it, and checks persisted data for all nine pairs below. Each pair uses
`processors: []`; the bracketed text is its pytest parameter ID.

| Source | Sink | Existing YAML case | Representative processed coverage |
| --- | --- | --- | --- |
| CSV | CSV | `[csv-csv]` | Direct Python, YAML/Python equivalence, and installed CLI |
| CSV | Parquet | `[csv-parquet]` | No additional processed case needed for this format boundary |
| CSV | SQLite | `[csv-sql]` | Direct Python mixed-I/O pipeline |
| Parquet | CSV | `[parquet-csv]` | No additional processed case needed for this format boundary |
| Parquet | Parquet | `[parquet-parquet]` | Direct Python processor chain |
| Parquet | SQLite | `[parquet-sql]` | New installed CLI processor chain |
| SQLite | CSV | `[sql-csv]` | Direct Python mixed-I/O pipeline |
| SQLite | Parquet | `[sql-parquet]` | New installed CLI processor chain |
| SQLite | SQLite | `[sql-sql]` | Direct Python parameterized query and filter |

A processed version of every pair at every layer would repeat the same
interfaces. The selected chains establish processor composition; the existing
nine-case test establishes unprocessed source/sink connectivity.

## Test mapping and assertions

All paths below are relative to `tests/`.

| Boundary or interaction | Test | Assertions |
| --- | --- | --- |
| Direct CSV copy | `functional/test_csv_pipeline.py::test_csv_pipeline_transfers_data_between_files` | Exact header, record values, and order |
| Direct CSV chain | `functional/test_csv_pipeline.py::test_csv_pipeline_applies_column_transformations` | Selection, rename, filtering, and exact persisted CSV |
| Direct Parquet chain | `functional/test_parquet_pipeline.py::test_local_parquet_pipeline_transforms_and_writes_data` | Exact output rows, column order, int32 type, mixed field nullability, and exclusion of null comparisons |
| Direct SQL chain | `functional/test_sql_pipeline.py::test_sql_pipeline_queries_transforms_and_writes_records` | Bound query parameters, filtering, and persisted SQL values |
| Direct CSV/SQL boundaries | `functional/test_mixed_io_pipeline.py::TestMixedIoPipeline::test_csv_source_to_sql_sink` and `test_sql_source_to_csv_sink` | Filtered values across both directions |
| YAML/direct-Python equivalence | `functional/test_yaml_pipeline.py::test_yaml_csv_pipeline_matches_equivalent_direct_python_composition` | Order-dependent select/rename/filter chain; expected rows, output fields, and equivalent Arrow tables |
| All YAML source/sink pairs | `integration/test_configured_pipeline_combinations.py::test_supported_source_sink_combination_runs_end_to_end` | All nine pairs; persisted rows and order; strengthened CSV/Parquet field names, order, inferred types, and nullability |
| Installed CSV CLI | `functional/test_cli_installed.py::test_installed_cli_run_executes_csv_pipeline` | Real executable, three processors, successful exit, and exact CSV output |
| Installed Parquet/SQL CLI | `functional/test_cli_installed.py::test_installed_cli_runs_processed_parquet_sql_pipeline[parquet-sql]` | YAML validation, order-dependent processor chain, persisted values/nulls, existing SQL row retained, and successful exit |
| Installed SQL/Parquet CLI | `functional/test_cli_installed.py::test_installed_cli_runs_processed_parquet_sql_pipeline[sql-parquet]` | Bound SQL parameters, YAML validation, processor order, persisted values/nulls, exact output Arrow schema, and successful exit |
| File serialization round trips | `integration/test_file_round_trip.py::TestFileRoundTrip` | CSV values and Parquet values/types/nulls |
| SQL conversion round trip | `integration/test_sql_round_trip.py::TestSqlRoundTrip::test_sql_sink_output_can_be_read_by_sql_source` | Values, nulls, field order, and expected inferred Arrow schema |

The installed CLI tests reuse the existing session-scoped `installed_cli`
fixture. It builds one wheel, installs it with locked runtime dependencies in
an isolated environment, verifies import isolation, and runs subprocesses from
temporary working directories. No additional installation fixture or test
framework is introduced.

The two new CLI cases verify that `validate` leaves the destination unchanged
before `run`. They reuse the existing YAML-writing, file-configuration, and
subprocess helpers. SQLite databases and Parquet files are temporary; no
external database service or credentials are required.

## Schema interpretation

CSV and SQL outputs are checked against their expected inferred types for the
chosen records. These assertions do not promise preservation of arbitrary
source schemas through CSV serialization or SQL value inference.

The direct Parquet pipeline explicitly starts with an int32 field and both
nullable and nonnullable fields. Its output must preserve those field contracts
through select, rename, filter, and serialization. A null predicate input is
excluded; the installed CLI cases separately preserve a null in a retained
output field.

## Scope of this ticket

Only two new parametrized cases are added. Existing tests receive stronger
assertions and input schemas; production code and public APIs are unchanged.

Failure matrices, malformed inputs, cleanup, partial-write failure scenarios,
and redaction completeness remain assigned to 0.9.0-05. The complete declared
Python/platform installation matrix remains assigned to 0.9.0-06.

## Verification and acceptance

Verified on Linux / CPython 3.12.14 with locked project dependencies:

- Full unit, integration, and functional suite: **710 passed**.
- Configured statement/branch coverage: **100%**.
- Ruff lint and formatting: passed.
- Pyright: zero errors and warnings.
- Strict MkDocs build and `git diff --check`: passed.

Acceptance criteria satisfied by this change:

- [x] Supported boundaries map to named existing or new tests.
- [x] CSV, Parquet, and SQLite each have verified source and sink coverage.
- [x] Pipelines with and without processors are covered.
- [x] YAML construction and the installed CLI have representative end-to-end coverage.
- [x] Assertions verify persisted values and relevant schema behavior.
- [x] Required pairs pass with only two additional cases, rather than a repeated Cartesian product.

These results describe the local working change. Integration into `dev` and
required CI checks remain necessary before closing the ticket.
