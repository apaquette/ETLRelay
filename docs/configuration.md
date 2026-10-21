# YAML Configuration

ETLRelay v0.8.0 supports declarative pipelines using versioned YAML
configuration. Schema version `1` defines a closed set of supported
sources, processors, sinks, storage backends, and file formats.

Configuration validation checks the documented schema and component
properties. Pipeline construction performs additional component-registration
resolution and SQL connection-reference preflight before invoking component
factories.

These checks detect supported configuration errors before execution,
but they do not guarantee successful filesystem access, database operations,
data processing, or output persistence.

Configuration schema version `1` is independent of the ETLRelay package
version and remains unchanged in v0.8.0.

Use this page as the canonical reference for the schema. [Getting Started](getting-started.md) demonstrates how to load, build, and execute a configuration; the [configuration architecture pages](architecture/configuration-loading.md) explain the internal boundaries.

## Configuration lifecycle

Configuration loading, schema validation, component construction, and
pipeline execution are separate stages:

1. `ConfigLoader` opens and parses the configuration document through
   `FileSystem` and `KeyValueReader`. `YamlReader` is the built-in
   configuration reader.
2. `ConfigValidator` checks schema version `1`, required properties,
   component types, and component-specific configuration rules.
3. `PipelineBuilder` resolves the configured component registrations
   and preflights SQL connection environment-variable references.
4. After registration resolution and SQL preflight succeed, the builder
   invokes component factories and returns a `Pipeline`.
5. The caller executes the pipeline and closes the builder afterward
   to release SQL engines owned by the shared factory.

The CLI exposes this workflow through `etlrelay validate` and
`etlrelay run`, with distinct validation/construction and execution
error reporting.

### Preflight guarantees

The supported validation and preflight checks establish that:

- The YAML document satisfies the required parsing and root-shape rules.
- The configuration uses schema version `1`.
- Required configuration properties are present and have supported types.
- Unsupported properties and component types are rejected.
- Configured components resolve through explicit registrations.
- SQL `connection_url_env` values are valid environment-variable names.
- Referenced SQL connection environment variables are present and
  nonempty during builder preflight.
- Component factories are not invoked if registration resolution or
  required SQL environment preflight fails.

Schema validation does not execute source queries, process records,
write pipeline output, or verify the compatibility of actual data
with the configured processors and destinations.

### Preflight limitations

Successful configuration validation does not establish that:

- Input files exist, are accessible, or contain valid data.
- Output paths are writable or have sufficient available storage.
- SQL connection URLs represent reachable databases.
- Database credentials have the necessary permissions.
- SQL queries are valid, authorized, or guaranteed to succeed.
- Destination tables exist or accept the processed data.
- Processors will accept every batch encountered during execution.
- Different batches will have compatible Arrow schemas.
- Execution will be atomic or recover automatically from failures.

The configuration document itself must be read during validation.
Pipeline construction may allocate resources for configured components.

`etlrelay validate` checks the configured pipeline without executing
its data-processing run. It is not a comprehensive runtime-readiness
or security assessment.

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
| `connection_url_env` | Yes | valid environment-variable identifier | Name of an environment variable containing a SQLAlchemy connection URL; literal URLs are not accepted in this field. |URL. |
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
| `connection_url_env` | Yes | valid environment-variable identifier | Name of an environment variable containing a SQLAlchemy connection URL; literal URLs are not accepted in this field. |
| `table_name` | Yes | non-empty string | Existing destination table to append rows to. |
| `schema` | No | non-empty string | Optional database schema name. |

The destination table must already exist and accept the processed batch columns. The sink does not create, truncate, replace, or migrate tables. Each non-empty batch is written in its own transaction; a later failure does not roll back earlier committed batches. SQLite is the reference integration-test backend. Other SQLAlchemy dialects require their relevant drivers and independent verification.

SQL source and sink components can use the same environment-variable name or different names.

The configuration validator rejects `connection_url_env` values that
do not have valid environment-variable identifier syntax. It does not
interpret arbitrary strings or literal SQLAlchemy connection URLs as
environment-variable references.

`PipelineBuilder` checks that each required variable resolves to a
nonempty value before invoking component factories. It does not
validate the contents of the resolved URL, establish a database
connection as part of preflight, or verify database authorization.

Connection values must be supplied securely by the application's
execution environment.

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

## Operational semantics

The configuration schema determines which components can be constructed. Runtime behavior follows the contracts of `Pipeline` and the selected source, processor, sink, and format implementations.

### Empty sources and zero-row batches

A source that produces no batches causes the pipeline to finish without invoking its sink.

A zero-row batch is different: it passes through the configured processors and participates in pipeline output-schema validation. If processing succeeds, it is delivered to the sink.

The concrete sink or writer determines how such a batch is persisted.

- `CsvWriter` can write a CSV header for a schema-bearing zero-row batch.
- `ParquetWriter` can write a valid zero-row Parquet file. A directly supplied empty iterable raises `WriterError` because no output schema can be established.
- `SqlSink` skips zero-row batches before opening a transaction or validating destination columns.

### Output schema compatibility

The first processed batch establishes the expected pipeline output schema, including when it contains zero rows.

Subsequent processed batches must have matching field names, field order, Arrow types, and nullability. Schema metadata differences are ignored.

An incompatible batch raises `ValueError` before being passed to the sink. ETLRelay does not automatically cast values, reorder fields, or reconcile incompatible schemas.

### Output files and transactions

Local file output uses truncating write mode. An existing output file is truncated when it is opened for writing, and a failed operation may leave an empty or partially written file.

An entirely empty pipeline source does not invoke the sink, so it does not truncate an existing output file through `FileSink`.

SQL output is append-only. Each nonempty batch is written in its own transaction. A failed transaction is rolled back according to the database and SQLAlchemy transaction behavior, but previously committed batches remain committed.

ETLRelay does not provide atomic file replacement, pipeline-wide transactions, automatic retries, or rollback of all previously written output.

### Resource cleanup

File streams acquired by `FileSource` and `FileSink` are closed when their operations complete or fail.

`Pipeline` attempts to close active processing and source iterators on termination when they expose callable `close()` methods.

Configuration-built pipelines use a shared `SqlEngineFactory` managed by `PipelineBuilder`. The caller must close the builder after execution, including when execution raises an exception.

Direct Python SQL components borrow their supplied engines; the application retains responsibility for disposing of those engines.

For detailed contracts, see [Pipeline](architecture/pipeline.md), [File Sink](architecture/file_sink.md), [Reader and Writer](architecture/reader_and_writer.md), and [SQL Source and Sink](architecture/sql_source_and_sink.md).

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
