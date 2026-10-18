# YAML Configuration

ETLRelay 0.6.0 supports declarative pipeline configuration using a versioned YAML document. Configuration schema version `1` exposes the built-in components only; it is not a general-purpose plugin system and does not permit arbitrary Python construction.

Use this page as the canonical reference for the schema. [Getting Started](getting-started.md) demonstrates how to load, build, and execute a configuration; the [configuration architecture pages](architecture/configuration-loading.md) explain the internal boundaries.

## Configuration lifecycle

Configuration loading, validation, construction, and execution are separate stages:

1. `ConfigLoader` opens and parses the configuration document through `FileSystem` and `KeyValueReader` (`YamlReader` is the built-in implementation).
2. `ConfigValidator` checks schema version 1 and delegates to the source, ordered processor-sequence, and sink validators. It raises `ConfigurationError` for schema failures.
3. `PipelineBuilder` resolves the source, sink, and processor registrations, then preflights SQL environment-variable references.
4. Only after component types and SQL references pass preflight does the builder invoke component factories and return a `Pipeline`.
5. The caller runs the pipeline with `pipeline.run()` and closes the builder after execution to release SQL engines owned by the shared factory.

The configuration file itself must be opened to read it. Invalid schema and missing/empty SQL connection variables are rejected before source/sink data operations begin. This is not a guarantee against runtime file, query, database, schema, processor, or sink failures.

## Root schema

Every schema-v1 document must contain exactly these top-level properties:

| Property | Required | Type | Contract |
|---|---:|---|---|
| `version` | Yes | integer | Must be the integer `1`; YAML Boolean `true` is not accepted as version 1. |
| `source` | Yes | mapping | One supported source definition. |
| `processors` | Yes | list | Ordered processor definitions. An empty list is valid and passes batches through unchanged. |
| `sink` | Yes | mapping | One supported sink definition. |

Unknown top-level properties are rejected. Component definitions also have closed property sets, so misspelled or unsupported fields are rejected rather than ignored. Duplicate YAML mapping keys are rejected, including duplicates after YAML merge-key flattening.

The schema version is independent of the ETLRelay package version. Version 1 has no implicit fallback or migration. Incompatible configuration-structure changes require a new schema version; existing version-1 property meanings must remain stable.

## Supported component/property matrix

| Area | `type` / name | Properties beyond `type` | Notes |
|---|---|---|---|
| Source | `file` | `path`, `format`, `storage` | Format must support reading. |
| Source | `sql` | `connection_url_env`, `query`; optional `parameters` | Uses a preflighted connection URL from the named environment variable. |
| Sink | `file` | `path`, `format`, `storage` | Format must support writing. |
| Sink | `sql` | `connection_url_env`, `table_name`; optional `schema` | Appends to an existing table. |
| Processor | `select_columns` | `columns` | Ordered list of unique string column names. |
| Processor | `rename_columns` | `mapping` | Mapping of string source names to string target names. |
| Processor | `filter_rows` | `column`, `operator`, `value` | Predicate value must be a string, integer, float, or Boolean. |
| Storage | `local` | Optional `base_path` | Defaults to `.`. |
| File input format | `csv`, `parquet` | `source.format` | Each registered format must support reading. |
| File output format | `csv`, `parquet` | `sink.format` | Each registered format must support writing. |

No other source, sink, processor, storage backend, or file format is supported by schema version 1.

## File source and sink

A file source and file sink use the same required property names:

| Property | Required | Type | Meaning |
|---|---:|---|---|
| `type` | Yes | string: `file` | Selects the file source or sink. |
| `path` | Yes | non-empty string | Input or output path. |
| `format` | Yes | string: `csv` or `parquet` | Explicitly selects a registered reader or writer. Format is not inferred from the filename extension. |
| `storage` | Yes | mapping | Storage component configuration. |
| `storage.type` | Yes | string: `local` | Selects `LocalFileSystem`. |
| `storage.base_path` | No | non-empty string | Permitted base directory; defaults to `.`. |

Relative `base_path` values are resolved from the process working directory; relative `path` values are resolved under that base directory. Absolute paths are accepted only if they remain within the configured base. `PathValidator` enforces path containment; it is not a complete OS-level sandbox.

The base directory and any needed parent directories must already exist. Local output creates a new file if necessary and truncates an existing output file; it does not create missing parent directories.

Source and sink formats are selected independently, so all four file-to-file combinations are supported: CSV→CSV, CSV→Parquet, Parquet→CSV, and Parquet→Parquet.

## SQL source

| Property | Required | Type | Meaning |
|---|---:|---|---|
| `type` | Yes | string: `sql` | Selects `SqlSource`. |
| `connection_url_env` | Yes | non-empty string | Name of an environment variable containing the SQLAlchemy connection URL. |
| `query` | Yes | non-empty string | Caller-authored SQL query. Use named bind parameters for query values. |
| `parameters` | No | mapping | Named bind-parameter values. Keys must be strings; values may be strings, integers, floats, Booleans, or `null`. |

Nested mappings and sequences are not supported as query-parameter values. Bound parameters are for values, not identifiers such as table or column names. Configuration validation does not parse SQL or enforce database authorization policy.

Example:

```yaml
source:
  type: sql
  connection_url_env: ETLRELAY_SOURCE_DATABASE_URL
  query: "SELECT id, amount, state FROM source_records WHERE state = :state ORDER BY id"
  parameters:
    state: ready
```

## SQL sink

| Property | Required | Type | Meaning |
|---|---:|---|---|
| `type` | Yes | string: `sql` | Selects `SqlSink`. |
| `connection_url_env` | Yes | non-empty string | Name of an environment variable containing the SQLAlchemy connection URL. |
| `table_name` | Yes | non-empty string | Existing destination table to append rows to. |
| `schema` | No | non-empty string | Optional database schema name. |

The destination table must already exist and accept the processed batch columns. The sink does not create, truncate, replace, or migrate tables. Each non-empty batch is written in its own transaction; a later failure does not roll back earlier committed batches. SQLite is the reference integration-test backend. Other SQLAlchemy dialects require their relevant drivers and independent verification.

SQL source and sink components can use the same environment-variable name or different names.

## Processor definitions

The `processors` property is an ordered list. Processor `n` receives the output of processor `n-1`. An empty list is valid; omitting the property is invalid.

### `select_columns`

| Property | Required | Type | Contract |
|---|---:|---|---|
| `type` | Yes | string: `select_columns` | Processor discriminator. |
| `columns` | Yes | list of strings | Names must be unique. The list determines output column order. |

Column existence depends on the data schema and can fail during execution.

### `rename_columns`

| Property | Required | Type | Contract |
|---|---:|---|---|
| `type` | Yes | string: `rename_columns` | Processor discriminator. |
| `mapping` | Yes | mapping of string to string | Source column name to desired column name. |

The validator checks that the mapping and its keys/values have the required types. Whether source columns exist and whether final column names conflict is checked against the batch schema during processing.

### `filter_rows`

| Property | Required | Type | Contract |
|---|---:|---|---|
| `type` | Yes | string: `filter_rows` | Processor discriminator. |
| `column` | Yes | non-empty string | Column to compare. |
| `operator` | Yes | string | One of `==`, `!=`, `<`, `<=`, `>`, `>=`. |
| `value` | Yes | string, integer, float, or Boolean | `null`, mappings, and sequences are not accepted. |

Column existence and comparison compatibility depend on the input data and may therefore fail at execution time. The validator does not inspect file contents or execute the processor.

## Supported source/sink combinations

The configured source and sink are independently selected from the supported formats and component types. This produces nine format/component combinations:

| Source | Sink | Status and constraints |
|---|---|---|
| CSV file | CSV file | Supported. |
| CSV file | Parquet file | Supported. |
| Parquet file | CSV file | Supported. |
| Parquet file | Parquet file | Supported. |
| CSV file | SQL | Supported. SQL target table must exist and accept the output columns. |
| Parquet file | SQL | Supported. SQL target table must exist and accept the output columns. |
| SQL | CSV file | Supported. Output path/base directory must be permitted and available. |
| SQL | Parquet file | Supported. Output path/base directory must be permitted and available. |
| SQL | SQL | Supported. Target table must exist and accept the output columns; source and sink may use same or separate connection variables. |

These are supported combinations, not a guarantee that arbitrary queries, schemas, paths, values, or destination tables will work. Runtime checks and external system errors still apply.

## Complete runnable examples

The repository's `examples/configuration/` directory contains nine schema-v1 YAML files for the combinations above, a reusable runner, a data-preparation script, and input setup for local CSV, Parquet, and SQLite. See [Getting Started](getting-started.md) for setup and run commands. The examples use a small schema with `id`, `amount`, and `state` columns; the pipeline selects `id` and `amount`, filters `amount >= 0`, and renames `id` to `record_id`.

- [Example runner](https://github.com/apaquette/ETLRelay/blob/v0.6.0/examples/configuration/run.py)
- [Prepare example data](https://github.com/apaquette/ETLRelay/blob/v0.6.0/examples/configuration/prepare_demo_data.py)
- [Configuration examples directory](https://github.com/apaquette/ETLRelay/tree/v0.6.0/examples/configuration)

The examples expect commands to be run from the repository root so relative paths are interpreted consistently. The SQL examples require the environment variables shown below to point at the SQLite demo databases created by `prepare_demo_data.py`:

```bash
export ETLRELAY_SOURCE_DATABASE_URL="sqlite:///examples/configuration/data/source.db"
export ETLRELAY_SINK_DATABASE_URL="sqlite:///examples/configuration/data/sink.db"
```

Only examples that use SQL need the corresponding variable. The values above are non-secret local SQLite URLs; real connection URLs may contain credentials and must not be placed directly in YAML.

## Environment variables and secrets

The configuration stores the **environment-variable name**, not the resolved URL. For example, `connection_url_env: ETLRELAY_SOURCE_DATABASE_URL` tells the builder which environment variable to resolve.

- Set required variables in the process environment before building a SQL pipeline.
- Missing and empty variable values cause preflight to fail before ETL component factories are invoked or source/sink I/O begins.
- Each unique referenced variable is resolved once during preflight.
- Error messages identify the configuration path and variable name, but must not include the resolved URL or credentials.
- Never put passwords, tokens, or credential-bearing connection URLs directly in YAML examples or commit them to version control.

Environment variables provide secret indirection, not a dedicated secrets vault. Deployment-specific secret injection, access control, rotation, and environment hygiene remain the application's responsibility. See [Security](security.md).

## Validation and representative errors

Validation rejects malformed documents and unsupported configuration before runtime construction. Examples of actionable error messages include:

| Problem | Example message |
|---|---|
| Unsupported schema version | `version must be the integer 1.` |
| Missing root field | `Required top-level field 'processors' is missing.` |
| Unsupported property | `sink.destination is not a supported field.` |
| Unsupported format | `source.format 'xlsx' is not supported for reading.` |
| Invalid filter operator | `processors[0].operator must be one of '==', '!=', '<', '<=', '>', '>='.` |
| Missing SQL environment variable | `source.connection_url_env references missing or empty environment variable 'ETLRELAY_SOURCE_DATABASE_URL'.` |

The full SQL preflight error is wrapped in `PipelineBuildError`; it may aggregate multiple missing references into one message. Component validators normally return lists of path-qualified errors; the root `ConfigValidator` raises `ConfigurationError` containing those validation errors.

YAML syntax/document errors are distinct from schema errors. `YamlReader` rejects malformed YAML, duplicate mapping keys, multiple documents, a non-mapping root, and non-string root keys. `ConfigLoader` does not translate filesystem or reader exceptions into `ConfigurationError` by default.

Validation does not guarantee that source files exist, SQL parses or executes, destination tables exist, columns match the data, or output operations will succeed. Those conditions depend on runtime components and external resources.

## Schema security and scope

- YAML is parsed with a safe loader; arbitrary Python object construction is not part of configuration loading.
- Component types resolve only through explicit built-in registries. Schema v1 does not provide dynamic imports, user code evaluation, or arbitrary plugin loading.
- SQL text remains caller-authored SQL. Bind values rather than interpolating untrusted values, and validate/allowlist dynamic identifiers separately.
- Local path validation is a containment check, not a full OS sandbox or authorization policy.
- JSON configuration, remote storage, additional formats, additional processors, a general plugin system, a CLI, schema migrations, and SQL table-creation modes are not part of the v0.6.0 YAML contract.
