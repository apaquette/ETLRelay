# ETLRelay v1.0.0 — Stable Initial Release

Release date: **2026-10-21**.

ETLRelay v1.0.0 establishes the stable public contract for the feature set
completed and verified in v0.9.0. It supports synchronous pipelines using
local CSV/Parquet or SQL input/output, the existing processors, direct Python
composition, YAML configuration, and the CLI.

## What's Changed

### Stable Public Contract

- Publish the [compatibility and versioning policy](../compatibility.md) for
  documented Python imports, constructors/protocols, data and failure semantics,
  YAML schema version 1, CLI behavior, and supported environments.
- Define patch/minor/major release rules and public deprecation/migration policy.
- Retain `TabularReader`/`TabularWriter` and the separate mapping-document
  `KeyValueReader` contract introduced before the API freeze.

### Release and Documentation Readiness

- Update package metadata, installation commands, CLI version examples, security
  policy, release documentation, and version-pinned content links for v1.0.0.
- Complete the v0.9.0 publication record and retain its review evidence.
- Verify release artifacts and supported environments using the existing checks.
- Establish maintainer verification as the acceptance mechanism; external beta
  feedback and release candidates are optional.

### Post-v1.0 Direction

- Replace detailed pre-1.0 milestone checklists with a concise release history
  and a [selected post-v1.0 plan](../roadmap.md#post-v100-roadmap).
- Expand the selected plan through targeted 1.1–1.14 milestones: SQL batching,
  PostgreSQL/MySQL/MariaDB/SQL Server/Oracle, common transformations, S3/Azure/GCS,
  Excel/JSON/Arrow interchange, trusted extensions, directory/regex consolidation,
  partitioned datasets,
  append/upsert/overwrite modes, APIs, watermark loads, DuckDB, and cloud warehouses.
- Target Python 3.15 through a separately verified dependency/compatibility
  upgrade. Require separate dependency and account-backed verification for
  Snowflake/BigQuery. Keep document pipelines, specialist integrations,
  continuous streaming and distributed execution subject to explicit review.
- Separate tentative future features from the selected milestones, with explicit
  feasibility/need conditions. Retain all new work outside v1.0.0 support until
  implemented and released.

## Upgrading

Applications using v0.9.0 require no Python or YAML migration. The runtime source,
constructor/protocol signatures, processors, schema version, CLI commands and exit
codes, dependency bounds, cleanup behavior, and persistence semantics are unchanged.
Install the stable release with:

```bash
python -m pip install etlrelay==1.0.0
```

For releases before v0.9.0, follow the
[v0.9.0 migration guide](migration-v0.9.0.md), including the tabular protocol rename.
The former `Reader`/`Writer` class names have no compatibility aliases.

## Support and Known Limitations

CPython 3.12–3.14 is supported in the five declared combinations: Ubuntu with
3.12/3.13/3.14, macOS with 3.12, and Windows with 3.12. The full suite runs on
Ubuntu/3.12; both-artifact smoke checks cover the other entries. SQLite is the
tested database. Other SQLAlchemy dialects need drivers and independent
verification and are not guaranteed support.

Local output writes are non-atomic and may truncate or leave partial/unreadable
files. SQL sinks append to existing compatible tables with per-batch transactions;
earlier commits survive later failures. SQL source results are materialized in
memory. Path containment is not a sandbox; ETLRelay-controlled diagnostics do not
sanitize arbitrary third-party exceptions or application logs.

S3/HDFS, additional formats/processors/integrations, mapping-document writing,
generic record conversion, dynamic plugins, SQL creation/upsert or pipeline-wide
transactions, scheduling, retries, and concurrent/distributed execution remain
outside this release's scope. Future capabilities will be evaluated through a
separate post-v1.0 roadmap.

See the [scope policy](v1-scope.md), [API reference](../api-reference.md),
[security guidance](../security.md), and [readiness record](release-v1.0.0.md)
for contracts, evidence, and release gates. Report reproducible defects with
synthetic data through [GitHub Issues](https://github.com/apaquette/ETLRelay/issues);
report suspected vulnerabilities privately through the
[Security Policy](https://github.com/apaquette/ETLRelay/blob/v1.0.0/SECURITY.md).
