# YAML Configuration Contract

**Configuration schema version:** `1`

This document defines the initial declarative configuration surface for ETLRelay. It exposes existing components only; it does not define a general plugin mechanism or custom component loading.

## Top-level structure

Every configuration must contain exactly these top-level properties:

- `version`: required integer; the only supported value is `1`.
- `source`: required source definition.
- `processors`: required ordered list of processor definitions. An empty list is valid and passes batches through unchanged.
- `sink`: required sink definition.

Unknown top-level properties are rejected. Each component definition also uses a closed set of properties: misspelled or unsupported properties are rejected rather than silently ignored. Duplicate YAML mapping keys are rejected.

The schema version is independent of the ETLRelay package version. An unsupported or missing schema version is an error; there is no implicit fallback or migration. Existing version-1 property meanings must not change. Incompatible changes to the configuration structure require a new schema version. For this small fixed component set, the contract is documented here and implemented with explicit Python validation; a separate JSON Schema file and schema-validation dependency are not required for v0.6.0.

## Supported components

| Area | YAML type/name | Supported properties |
|---|---|---|
| Source | `file` | `path`, `format`, `storage` |
| Source | `sql` | `connection_url_env`, `query`, optional `parameters` |
| Sink | `file` | `path`, `format`, `storage` |
| Sink | `sql` | `connection_url_env`, `table_name`, optional `schema` |
| Processor | `select_columns` | `columns` |
| Processor | `rename_columns` | `mapping` |
| Processor | `filter_rows` | `column`, `operator`, `value` |
| Storage | `local` | optional `base_path` |
| File input format | `csv`, `parquet` | Selected by the file source's `format` |
| File output format | `csv`, `parquet` | Selected by the file sink's `format` |

No other source, sink, processor, storage backend, or file format is supported by schema version 1.

## File source and sink

A file source or sink has these properties:

| Property | Required | Type | Meaning |
|---|---|---|---|
| `type` | Yes | string: `file` | Selects `FileSource` or `FileSink` |
| `path` | Yes | non-empty string | Path to the input or output file |
| `format` | Yes | string: `csv` or `parquet` | Selects the existing reader or writer |
| `storage` | Yes | mapping | Local-storage configuration |
| `storage.type` | Yes | string: `local` | Selects `LocalFileSystem` |
| `storage.base_path` | No | non-empty string | Permitted base directory; defaults to `.` |

Paths are interpreted through the existing `PathValidator`. A relative `base_path` is resolved from the process working directory. A relative `path` is resolved under that base directory. Absolute paths are accepted only when they remain within the configured base. Path validation is a containment check, not a complete operating-system sandbox.

Output behavior remains that of `LocalFileSystem`: an existing output file is truncated, a new output file can be created, and missing parent directories are not created automatically. The base directory and any required parent directories must already exist.

The source and sink formats are independent. All four file-to-file combinations are allowed: CSV→CSV, CSV→Parquet, Parquet→CSV, and Parquet→Parquet.

## Supported source/sink combinations

| Source | Sink | Status and constraints |
|---|---|---|
| `file` | `file` | Supported. Source and sink formats are selected independently from CSV and Parquet. |
| `file` | `sql` | Supported. The target SQL table must already exist and accept the processed batch columns. |
| `sql` | `file` | Supported. The SQL query supplies rows; the file sink selects CSV or Parquet output. |
| `sql` | `sql` | Supported. The target table must already exist and accept the processed batch columns. Source and sink may use the same or different connection URL environment variables. |

These combinations describe component compatibility, not guaranteed successful execution for every dataset. Runtime schema, query, database, and filesystem errors still propagate from the existing components.

## SQL source

A SQL source has these properties:

| Property | Required | Type | Meaning |
|---|---|---|---|
| `type` | Yes | string: `sql` | Selects `SqlSource` |
| `connection_url_env` | Yes | non-empty environment-variable name | Name of the environment variable containing the SQLAlchemy connection URL |
| `query` | Yes | non-empty string | SQL query to execute; use SQLAlchemy named bind parameters for values |
| `parameters` | No | mapping of string names to scalar values | Named bind parameter values; omitted means no parameters |

Parameter values are limited to YAML strings, integers, floats, booleans, and null. Nested mappings and sequences are not supported as query parameter values. Bind parameters represent values, not SQL identifiers.

The environment-variable property stores the **variable name**, never the connection URL or credentials themselves. If the variable is missing or empty, configuration building fails before source or sink I/O begins. Error messages must not print the resolved connection URL or its credentials.

## SQL sink

A SQL sink has these properties:

| Property | Required | Type | Meaning |
|---|---|---|---|
| `type` | Yes | string: `sql` | Selects `SqlSink` |
| `connection_url_env` | Yes | non-empty environment-variable name | Name of the environment variable containing the SQLAlchemy connection URL |
| `table_name` | Yes | non-empty string | Existing destination table to append to |
| `schema` | No | non-empty string | Optional database schema name |

The destination table must already exist. The sink appends rows; it does not create, truncate, replace, or migrate tables. Actual database support depends on the SQLAlchemy dialect and DBAPI driver. SQLite is the reference backend covered by project tests; other dialects are not guaranteed by this milestone.

A SQL source and sink may use the same environment-variable name or different names. A configuration may combine either source with either sink, subject to runtime query, schema, and database constraints.

The configuration builder creates the SQLAlchemy engines required by SQL components and is responsible for their lifecycle. It must not change the caller-owned engine lifecycle of the direct Python APIs. The concrete cleanup surface belongs to the pipeline-builder implementation, not to YAML fields.

## Processors

`processors` is an ordered list. Every entry must contain a recognized `type` and only properties allowed for that processor.

### `select_columns`

| Property | Required | Type |
|---|---|---|
| `type` | Yes | string: `select_columns` |
| `columns` | Yes | list of strings |

Column names must be unique. The list order defines the output column order. Whether a named column exists can only be checked once the source schema is available.

### `rename_columns`

| Property | Required | Type |
|---|---|---|
| `type` | Yes | string: `rename_columns` |
| `mapping` | Yes | mapping of string column names to string column names |

The mapping uses existing column names as keys and desired names as values. Final-name uniqueness and source-column existence are checked by the processor against the batch schema.

### `filter_rows`

| Property | Required | Type |
|---|---|---|
| `type` | Yes | string: `filter_rows` |
| `column` | Yes | non-empty string |
| `operator` | Yes | one of `==`, `!=`, `<`, `<=`, `>`, `>=` |
| `value` | Yes | string, integer, float, or boolean |

The filter value cannot be a mapping, sequence, or null. Column existence and comparison compatibility depend on the source data and may therefore fail at execution time.

An empty `processors: []` is valid. It is distinct from a missing `processors` property, which is invalid.

## Examples

### File-to-file CSV/Parquet pipeline

```yaml
version: 1

source:
  type: file
  path: data/input.csv
  format: csv
  storage:
    type: local
    base_path: "."

processors:
  - type: select_columns
    columns: [id, amount]
  - type: filter_rows
    column: amount
    operator: ">="
    value: 0
  - type: rename_columns
    mapping:
      id: record_id

sink:
  type: file
  path: data/output.parquet
  format: parquet
  storage:
    type: local
    base_path: "."
```

### SQL-to-SQL pipeline

Set `ETLRELAY_SOURCE_DATABASE_URL` and `ETLRELAY_SINK_DATABASE_URL` in the process environment before building the pipeline. Each variable contains the applicable SQLAlchemy connection URL; do not put credentials directly in YAML.

```yaml
version: 1

source:
  type: sql
  connection_url_env: ETLRELAY_SOURCE_DATABASE_URL
  query: "SELECT id, amount FROM source_table WHERE state = :state"
  parameters:
    state: ready

processors: []

sink:
  type: sql
  connection_url_env: ETLRELAY_SINK_DATABASE_URL
  table_name: processed_records
```

## Validation and security rules

- Parse YAML with a safe loader; do not construct Python objects from arbitrary YAML tags.
- Validate the entire configuration and resolve required environment-variable references before beginning pipeline execution or opening source/sink resources.
- Reject malformed YAML, duplicate mapping keys, missing required properties, incorrect types, unknown component names, unsupported properties, unknown schema versions, and unsupported combinations.
- Report the configuration location and property that failed validation. Do not include resolved secret values in errors.
- Use explicit mappings from the supported YAML type names to component constructors. Do not use `eval`, arbitrary imports, unrestricted reflection, or user-provided Python expressions.
- Treat SQL text as caller-authored SQL. Use bound parameters for values; configuration validation is not a SQL authorization or query-policy system.
- Do not add configuration options for remote storage, additional formats, table creation modes, or unsupported processors in schema version 1.
