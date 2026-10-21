# ETLRelay Roadmap

ETLRelay is a lightweight Python library and CLI for repeatable tabular ETL jobs.
Post-v1.0 development expands the jobs users can complete: common databases,
files and cloud storage; useful transformations; repeatable loads; and convenient,
explicit configuration. The library and CLI remain independently usable.

ETLRelay v1.0.0 establishes the stable release of the reviewed v0.9.0 runtime,
YAML schema version 1, and documented Python/CLI interfaces. See the
[release record](development/release-v1.0.0.md) for verification and release details.
Planned additions below are outside the
[v1.0 support policy](development/v1-scope.md) until implemented and released.

## Release summary

| Version | Status | Delivered outcome |
| --- | --- | --- |
| 0.1.0 / 0.1.x | Released | Initial Arrow-backed batch pipeline, local CSV workflows, and stabilization |
| 0.2.0 | Released | Batch/schema contracts and select, rename, and filter processors |
| 0.3.0 | Released | Parquet input/output through the file composition model |
| 0.4.0 | Released | Local storage, path, stream ownership, and failure contracts |
| 0.5.0 | Released | SQL query sources and append-only sinks; SQLite verification |
| 0.6.0 | Released | Versioned YAML configuration, validation, explicit registrations, and pipeline construction |
| 0.7.0 | Released | Installed CLI for validation, execution, help, and version reporting |
| 0.8.0 | Released | Security/operational controls, logging, cleanup, and artifact/compatibility checks |
| 0.9.0 | Released | Feature freeze, tabular protocol naming, API review, and pipeline/failure/documentation verification |
| 1.0.0 | Released | Stable compatibility policy and completed release documentation; runtime behavior retained from 0.9.0 |

Earlier milestone detail is retained in the
[tagged v0.9.0 roadmap](https://github.com/apaquette/ETLRelay/blob/v0.9.0/docs/roadmap.md)
and Git history. The maintained roadmap below governs post-v1.0 development.

## Post-v1.0.0 roadmap

This is the selected development direction, researched on **21 October 2026**.
Minor-version labels describe intended release themes and order, not dates,
current capabilities, or a promise to support every version of a technology.
Create focused implementation tickets before starting a milestone. Split a
milestone when its independently useful parts warrant separate releases; record
any scope or ordering changes rather than silently dropping selected work.

The plan extends beyond connectors. More destinations help adoption, but users
also need transformations, realistic file layouts, and repeatable loading.
Integration breadth must come with maintained installation instructions,
representative examples, and reproducible verification.

### Selected milestones

| Target | User outcome and selected scope | Main completion boundary / dependencies |
| --- | --- | --- |
| **1.1 — SQL scale and PostgreSQL** | Opt-in chunked SQL reads; verified PostgreSQL source/sink support | Stable cross-chunk schemas, driver buffering, early termination, cleanup, types and per-batch commits tested against a real PostgreSQL service. Preserve existing defaults. |
| **1.2 — Practical transformations** | Column casting; fill/drop nulls; string cleanup; date parsing; derived columns; richer explicit filters | Arrow-backed operations with documented null, overflow, timezone and invalid-value behavior. Restricted declarative operations, including membership, null tests and Boolean predicate composition; no arbitrary code evaluation. |
| **1.3 — Directory inputs and file consolidation** | Read multiple files from a directory, select filenames with a regular expression, and combine their batches into one destination | Deterministic discovery/order; explicit recursion and no-match behavior; consistent format/schema; per-file cleanup and failure propagation. Verify multiple CSV/Parquet inputs to one output file or SQL destination through Python, YAML and CLI. |
| **1.4 — S3 and MySQL-family databases** | S3 filesystem; verified MySQL and MariaDB reads/writes | Reuse SQL/storage contracts from 1.1. Test MySQL and MariaDB separately, using named driver/server versions. Verify cloud credentials, seekable Parquet reads, interrupted writes and cleanup. |
| **1.5 — Business data interchange** | Verified SQL Server; optional `.xlsx` reading/writing; deterministic filename-based format inference | Document driver/native installation and database type/transaction behavior. Define sheets, headers, dates, formulas versus cached values, and multi-batch workbook output. Explicit format wins; ambiguous suffixes fail clearly. |
| **1.6 — JSON and Arrow interchange** | JSON mapping configuration; tabular JSON Lines/NDJSON read/write; JSON array-of-records input; Arrow IPC/Feather v2 read/write | Keep mapping configuration separate from row data. Define schema, nesting, decimal/time serialization, empty data and bounded parsing. JSON-array input needs a suitable incremental parser; NDJSON output needs an explicitly tested serializer. |
| **1.7 — Trusted component extensions** | Explicitly enabled, installed custom source/processor/sink/storage/format components through the stock CLI | Existing Python composition/registries remain valid. Define extension names, validation/factories, collision policy, dependency diagnostics and compatibility tests. Configuration cannot silently import arbitrary executable code. |
| **1.8 — Partitioned datasets** | Extend the file-collection source from 1.3 with partitioned Parquet datasets; projection/filter pushdown where supported; compression options; explicit input schemas | Builds on directory discovery from 1.3, remote storage adapters and schema work. Define deterministic discovery, partition columns, file sizing, incompatible files, ordering, overwrite/collision rules and partial-dataset cleanup. Compression belongs to the appropriate format/stream layer. |
| **1.9 — Azure and Google Cloud storage** | Azure Blob Storage/ADLS Gen2 and Google Cloud Storage filesystem adapters | Reuse the remote storage behavior verified for S3. Test each service independently, including authentication, prefix boundaries, retries inherited from clients, seekability and failed uploads. Backend/Python/platform support may be narrower than the core package. |
| **1.10 — Enterprise destinations and write modes** | Verified Oracle support; explicit `append`, `upsert` and `overwrite` modes; opt-in destination-table creation; staged local-file replacement | Verify Oracle queries/types/reflection/transactions using a selected driver and real database. Introduce SQL modes first for SQLite/PostgreSQL, then other dialects explicitly. Publish a destination/format capability matrix. Define keys, duplicate/null keys, schema/type creation, one-time overwrite initialization, rollback and partial commits. Local replacement guarantees require same-filesystem staging; do not promise atomic publication on every storage backend. |
| **1.11 — HTTP/API ingestion** | HTTPS file input and a paginated REST JSON-record source | Depends on tabular record conversion from 1.6. Support explicit record paths, selected pagination modes, credential references, timeouts, request/page limits and bounded read retries. Prevent credential forwarding to untrusted pagination/redirect hosts. No universal SaaS connector or HTTP write retry guarantee. |
| **1.12 — Incremental jobs** | Watermark-based SQL/API extraction across runs; explicit persisted load state | Depends on load modes and source contracts. Define cursor ties, late data, overlap/replay, successful-state advancement, concurrent-run exclusion and restart behavior. Persist state only after the corresponding output is durable; document duplicate windows rather than claiming exactly-once delivery. |
| **1.13 — Embedded analytical workflows** | Optional DuckDB source/sink integration and job-level SQL transformations for joins, aggregates, sorting and deduplication | Use a maintained execution engine. Establish an explicit whole-job resource/lifecycle boundary, temporary storage, limits and cleanup. Global operations must see all relevant batches, not silently run once per batch. Verify Arrow interchange and actual spill/memory behavior. |
| **1.14 — Cloud warehouses** | Optional Snowflake and BigQuery integration | Separate feasibility/verification tickets per service. Resolve dialect/dependency compatibility, authenticate through supported methods, and fund reproducible account-backed tests. Define query types, supported writes, load costs and transaction boundaries independently; a SQLAlchemy dialect is not proof of equivalent SQL sink semantics. |

SQL Server, formats, processors and cloud adapters do not technically require
all earlier milestones. This sequence prioritizes reusable contracts and
complete user workflows; independent work can proceed without manufacturing
unnecessary dependencies. The higher-risk stateful/analytical milestones require
a design review before implementation, while preserving the stable v1 interfaces.

### Directory inputs and consolidation

Reading a directory of files into one destination is selected for 1.3, before
partitioned datasets. The initial implementation supports local CSV/Parquet
collections, with remote discovery added alongside the corresponding adapters.
A job selects one input directory and an optional filename regex, reads matching
files as one ordered stream of batches, applies its processor chain, and writes
to one sink. That sink may produce a single output file or write to a SQL table.

- Validate the regex before opening source files or the destination. Define
  full-match filename semantics; directory recursion must be explicitly enabled.
- Discover regular files in a deterministic order and define no-match behavior.
  Reject a destination that is also selected as an input.
- Use a common configured format and compatible schema. Format inference, when
  available, must not silently combine incompatible formats or schemas.
- Consume files incrementally and release each stream on completion or failure;
  do not materialize every file or open all streams at once.
- Feed the entire collection to one sink execution. Do not reopen/truncate the
  destination for each input file or repeat output headers between input files.
- Test empty files, zero-row batches, schema differences, invalid regexes,
  inaccessible files, failure in a later file, cleanup and partial output.

The initial collection source concatenates compatible rows. It does not join
records, deduplicate globally or reconcile incompatible schemas automatically.

### Destination write modes

The target public write-mode vocabulary is **`append`, `upsert`, `overwrite`**.
Support is explicit per destination, format and backend. Unsupported combinations
must fail clearly before destination modification; there is no silent fallback.

| Mode | Intended behavior | Required contract |
| --- | --- | --- |
| `append` | Add incoming rows while retaining existing destination data | Define schema compatibility, duplicate handling and format-specific append support. SQL append retains the existing per-batch transaction contract unless a separate option changes it. |
| `upsert` | Insert new keys and update matching keys | Require explicit key columns and define duplicate/null keys, update columns, conflicts and transaction boundaries. Initial support targets SQL sinks; keyed file updates are not implied. |
| `overwrite` | Replace the destination's data with the complete output of this job | Initialize replacement once per job, across all batches and source files. Define empty-job behavior, metadata preservation, failures and partial publication. Replacing table data does not implicitly authorize dropping/recreating the table. |

SQL initially targets all three modes on individually verified backends. File
support follows the format/storage capability matrix: CSV append must handle
headers correctly; a single Parquet file cannot be appended by concatenating
serialized bytes. Partitioned-dataset append has separate file-collision and
schema rules. Document unsupported modes for spreadsheets, objects and warehouses
instead of assuming that every sink offers every mode.

Existing v1.0 defaults remain compatible: SQL appends, while local file output
truncates an existing destination. Staged local-file overwrite is an opt-in
stronger publication behavior until deliberately selected by callers. Define
cleanup and same-filesystem replacement guarantees; cloud publication must not
inherit local atomicity claims.

### Processor boundaries

The first processor expansion targets operations that correctly transform one
`Batch` at a time. Proposed configuration concepts include casting named columns,
replacing nulls, trimming/normalizing strings, parsing dates, calculating columns
from named arithmetic/string/date operations, and combining explicit predicates.
Public names and constructor signatures are decided in the implementation review.

Do not call per-batch deduplication, sorting, aggregation or ranking a whole-job
operation. Forward/backward filling also needs explicit cross-batch semantics.
Global joins, group-by, sorting and deduplication belong in the analytical
milestone's separate execution boundary. They must not require breaking
`Processor.process(batch) -> Batch` or creating a new distributed engine.

### Data representations and schemas

A JSON/YAML mapping document describes one configuration object. A JSON array of
row mappings or an NDJSON stream describes tabular records; neither is a
`KeyValueReader` result. The JSON-record/API milestones provide concrete reasons
for narrow record-to-`Batch` and `Batch`-to-record adapters, with explicit schemas,
nulls, nesting and batching. They do not justify a generic conversion framework.

Keep current strict output-schema enforcement as the default. Explicit input
schemas and casting allow users to stabilize otherwise ambiguous data; automatic
schema evolution or silently widening output schemas is not part of this plan.
`KeyValueWriter` and general mapping-document pipelines remain deferred because
none of the selected output workflows requires them.

### Streaming and repeatability

CSV and Parquet already yield incremental batches. SQL chunking fills a specific
finite-input gap. A `fetchmany` loop alone does not establish bounded end-to-end
memory: verify each driver's cursor/buffering behavior and measure representative
jobs. SQL chunking must also document its effect on per-batch transactions.

Incremental loading in 1.12 is different: it remembers which records were loaded
between runs. Define state ownership and failure recovery explicitly. SDK read
retries may be useful; automatically retrying a partially committed pipeline is
not safe without a defined replay/idempotency contract. Continuous message/event
processing, CDC and exactly-once delivery are separate future decisions.

### Python compatibility and optional installations

**Selected compatibility track:** Target CPython 3.15 in the first minor release
that passes dependency/artifact/platform checks, aiming for 1.1. PyArrow 23 has no
CPython 3.15 wheels; PyArrow 26 publishes them. Upgrade after regression testing,
retain Python 3.12–3.14 compatibility, and verify declared environments before
changing support claims. This track need not block an otherwise complete feature.

Keep integrations with extra drivers/SDKs optional. Record supported combinations
per integration; an optional connector's narrower interpreter range must not
silently narrow core ETLRelay support. Prefer maintained Arrow filesystem adapters,
SQLAlchemy dialects and existing engine clients over independent connector stacks.

Provide documented installation extras where appropriate, usable examples,
a troubleshooting guide and a named driver/server test matrix. Cloud integrations
need real service checks as well as deterministic local tests. An emulator or
S3-compatible endpoint is verified separately; it does not prove all providers.

### Research and prioritization findings

The 2026 Stack Overflow survey reports PostgreSQL, SQLite, MySQL, SQL Server and
MariaDB among commonly used databases. This supports broadening relational
verification beyond SQLite/PostgreSQL/SQL Server. It measures surveyed developer
usage, not ETLRelay demand or a complete enterprise ETL market.

Arrow already supplies compute kernels, JSON Lines reading, dataset scanning and
partitioning, IPC formats, and S3/Azure/GCS/HDFS filesystem implementations.
These make substantial expansion feasible through adapters. Oracle also has an
included SQLAlchemy dialect and a Python driver whose Thin mode needs no Oracle
Client installation; a maintained real database test environment is still required.
ETLRelay still owns configuration, lifecycle, schema, failure and installation
guarantees. Arrow JSON reading does not by itself supply a JSON writer or a
JSON-array streaming parser.

DuckDB's Arrow integration and external-memory execution make it a useful local
analytical target before introducing Spark or a custom parallel runtime. Actual
query memory/spill behavior remains workload-dependent and must be measured.

Snowflake and BigQuery are promoted from unspecified future integrations to the
selected warehouse milestone, with explicit compatibility and account-test gates.
At this review, Snowflake's documented SQLAlchemy requirement is
`>=2.0.44,<2.1`, while ETLRelay's lockfile uses 2.1.5. The core requirement
`sqlalchemy>=2,<3` permits 2.0, but a resolver-compatible installation is only the
start: test supported dependency combinations or choose another maintained
integration path before claiming support. BigQuery likewise needs its own write
and transaction design rather than an assumption that it behaves like SQLite.

## Tentative future features — pending feasibility and need

The selected plan now includes processors, JSON records/conversion, additional
cloud storage, APIs, incremental loading and warehouse integrations that were
previously broadly deferred. The following remain unassigned. Review them against
a concrete workflow and a sustainable test/support plan, rather than excluding
them permanently or advertising them as available.

| Candidate | Assessment and next acceptance condition |
| --- | --- |
| **ClickHouse, Redshift, Athena, Trino and Databricks SQL** | Useful analytical integrations with differing dialects, authentication and write capabilities. Evaluate one service at a time; distinguish query-only support from tested sinks and bulk-loading paths. |
| **HDFS** | Feasible through Arrow, but adds Java/Hadoop native client installation, authentication and service-test costs. Promote when there is a maintained cluster/test image and a clear deployment use case. It does not require distributed ETL execution. |
| **Hive** | Potential SQL integration; establish maintained driver/dialect, authentication and read/write semantics with a reproducible service. Hive-style Parquet partitioning in 1.8 does not imply Hive server support. |
| **ORC, Avro, XML, legacy Excel and other formats** | ORC is a plausible Arrow-based addition; others require format-specific dependencies and schema/record rules. Promote a named format when representative interchange files and maintenance capacity justify it. `.xlsx` support does not imply `.xls`, macros or formula evaluation. |
| **SFTP/FTP and wider filesystem adapters** | A maintained fsspec-based bridge may cover useful transfer workflows. Establish credential, seek, publication and failure behavior per backend; an arbitrary protocol string must not imply verified support. Prefer SFTP where secure transfer is required. |
| **MongoDB, Elasticsearch and other document stores** | Potential tabular source/sink adapters, with explicit projection, nested-data mapping and bulk/error semantics. Their popularity alone does not settle the mapping-to-table contract. Redis is not prioritized as a general ETL destination. |
| **Spark and other execution engines** | An optional adapter may serve workloads beyond a single machine. Compare it with the selected local analytical approach; define deployment, schema, ownership and failure boundaries without rebuilding Spark inside ETLRelay. |
| **Parallel processing** | Benchmark native Arrow/DuckDB parallelism first. Add configurable worker execution only for a measured bottleneck with explicit ordering, backpressure, cancellation, state and serialization semantics. |
| **Distributed computing, Kafka/event streams and CDC** | Require separate checkpoint, replay, deployment and delivery contracts. Not implied by finite-batch streaming or watermark loads; no custom distributed runtime is planned. |
| **Mapping-document pipelines and `KeyValueWriter`** | Remain separate from tabular JSON/API records. Need a concrete document transformation/export workflow before adding public lifecycle or writer abstractions. |
| **Unrestricted expressions, automatic schema evolution and general DAG scheduling** | Broader languages/state/orchestration can alter core guarantees. First establish bounded use cases; prefer integration with existing tools over absorbing their execution platforms. |

## Delivery rules

- Preserve the [stable compatibility policy](compatibility.md): compatible fixes
  use patches, additions use minors, and incompatible public changes require a
  major-version proposal. Keep current defaults until compatible opt-ins ship.
- Start each feature with a user workflow, acceptance criteria, dependency/test
  costs and focused implementation tickets. Long-range scope can change through
  an explicit roadmap decision; it is not a v1.0 release requirement.
- Verify Python, YAML and CLI workflows, data/schema correctness, cleanup,
  secret handling, failed writes, installation and version-pinned documentation.
- Retain failure/partial-write guarantees until a named new mode changes them.
  Document transaction behavior per database; do not assume universal semantics.
- Record performance and memory baselines for representative larger jobs. Include
  useful safe run summaries and actionable component/driver diagnostics with
  relevant milestones; these are execution diagnostics, not a data-quality engine.
- Add support claims only after integration and built-artifact checks pass.
  Update the support record, examples, changelog and release notes together.
- Use maintainer reproductions without requiring an external user base. Review
  installation friction, maintenance cost and practical usability after releases.

## Technical references

Sources were reviewed on 21 October 2026. Dependency capabilities inform
feasibility; they do not establish ETLRelay support. Product priority is a
maintainer judgment, not a measured adoption forecast.

- [2026 Stack Overflow database survey](https://survey.stackoverflow.co/2026/technology/data/databases).
- [SQLAlchemy included/external dialects](https://docs.sqlalchemy.org/en/21/dialects/index.html)
  and [cursor/result streaming](https://docs.sqlalchemy.org/en/21/core/connections.html#using-server-side-cursors-a-k-a-stream-results).
- [Arrow 23 compute kernels](https://arrow.apache.org/docs/23.0/python/api/compute.html),
  [JSON input](https://arrow.apache.org/docs/python/json.html),
  [datasets](https://arrow.apache.org/docs/python/dataset.html), and
  [filesystems](https://arrow.apache.org/docs/python/filesystems.html).
- [PyArrow 26 published artifacts](https://pypi.org/project/pyarrow/26.0.0/).
- [Oracle Python driver installation and Thin mode](https://python-oracledb.readthedocs.io/en/stable/user_guide/installation.html)
  and [Oracle Database Free](https://www.oracle.com/database/free/).
- [DuckDB Python/Arrow integration](https://duckdb.org/docs/current/guides/python/sql_on_arrow)
  and [memory management](https://duckdb.org/2024/07/09/memory-management).
- [Snowflake SQLAlchemy requirements](https://docs.snowflake.com/en/developer-guide/sqlalchemy/sqlalchemy)
  and [Google's BigQuery dialect](https://googleapis.dev/python/sqlalchemy-bigquery/latest/README.html).
- [dlt incremental loading](https://dlthub.com/docs/general-usage/incremental-loading)
  and [merge strategies](https://dlthub.com/docs/general-usage/merge-loading),
  as examples of the state/write semantics repeatable ingestion must address.
- [GitHub REST API practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api),
  as a representative API's pagination, credentials and rate-limit concerns.