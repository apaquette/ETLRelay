# ETLRelay v0.9.0 — Release Notes

Release date: **2026-10-21**.

ETLRelay v0.9.0 freezes the intended v1.0 feature set and reviews its public API,
component interactions, failure behavior, documentation, and package installation.
The supported product remains synchronous pipelines using local CSV/Parquet or
SQL, the existing processors, YAML configuration, and the CLI.

## What's Changed

### Public API Review

- Rename `Reader` and `Writer` to `TabularReader` and `TabularWriter` to identify
  their batch-oriented contracts. The old class names are removed without aliases;
  the existing modules and concrete format-class names remain unchanged.
- Keep `KeyValueReader` separate for mapping-shaped documents. Mapping-document
  writing and generic tabular/row-record conversion remain deferred.
- Retain YAML configuration schema version `1` and the current CLI command set.

### Correctness and Failure Handling

- Report invalid YAML document shapes as CLI configuration failures with exit
  code `3`, using `YamlDocumentError`, a compatible `ValueError` subclass.
- Reject ambiguous column selection with `ValueError` and enforce unique final
  names when renaming columns, including duplicate input fields.
- Preserve the original error if Parquet finalization also fails. Report secondary
  cleanup failures without exposing their exception messages.

### Testing and Distribution Verification

- Record representative Python, YAML, and installed-CLI coverage across local
  CSV, Parquet, and SQLite source/sink boundaries.
- Extend failure coverage for borrowed streams, partial outputs, SQL connection
  and conversion failures, transaction behavior, and controlled diagnostics.
- Install wheels and source distributions separately outside the checkout.
- Check complete runtime dependency requirements, source modules, licence/notice
  files, and console entry points.
- Remove the unused Polars runtime dependency; retain PyArrow-based processing.

### Documentation

- Provide a self-contained CLI/Python quick start and verify shipped examples
  against a built, installed candidate.
- Document extension through Python protocols, schema/validation boundaries,
  troubleshooting, security limits, and migration requirements.
- Record the exact support matrix and the frozen v1.0 boundary.

### Dependencies and Tooling

- Refresh dependency and release tooling, including SQLAlchemy,
  Ruff, mkdocstrings, and GitHub Actions dependencies.

## Migration

Update imports and annotations from `Reader`/`Writer` to
`TabularReader`/`TabularWriter`. Review catches for ambiguous column selection
and CLI automation that previously treated invalid YAML document shapes as
internal failures. Applications using Polars must declare their own dependency.

See [Migration to v0.9.0](migration-v0.9.0.md) for import mappings and behavior
changes. No YAML schema migration is required.

## Support and Limitations

CPython 3.12–3.14 is supported in the five declared Python/platform combinations;
full tests run on Ubuntu/3.12, with installed-artifact smoke checks on the remaining
matrix entries. SQLite is the reference database; other SQLAlchemy dialects need
appropriate drivers and independent verification.

Local writes truncate existing files and are not atomic. SQL sinks append to
existing tables using per-batch transactions. SQL source results are materialized
in memory. Safe diagnostics do not sanitize arbitrary third-party exceptions or
application logging. Path containment is not a filesystem sandbox.

S3/HDFS, additional formats/processors, dynamic plugins, scheduling, automatic
retries, distributed execution, schema reconciliation, SQL table creation/upsert,
`KeyValueWriter`, and generic record conversion remain outside the v1.0 boundary.

The [scope policy](v1-scope.md), [API review](api-review.md),
[pipeline coverage](pipeline-coverage.md), [failure matrix](failure-matrix.md),
and [packaging verification](packaging-verification.md) provide supporting detail.
See [Beta readiness and feedback](beta-readiness.md) for the review decision,
verification evidence, remaining publication gates, and reporting criteria.
