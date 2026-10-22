# Security

ETLRelay v1.0.0 retains the reviewed security and operational contracts established in earlier releases.

The release includes regression-tested controls for local path containment, safe YAML configuration, SQL parameter handling, connection-secret references, error reporting, operational logging, and resource cleanup. Its CI workflow also checks dependencies and verifies built distribution artifacts.

These controls address specific risks. **ETLRelay does not provide a filesystem sandbox, SQL authorization boundary, secrets vault, or general-purpose environment for executing untrusted code.**

ETLRelay v1.0.0 provides a stable public contract. Applications remain responsible for evaluating suitability, permissions, and operational safeguards before processing sensitive or production data.

## Local filesystem paths

`PathValidator` resolves candidate paths and verifies that their resolved locations remain within the configured base directory.

This check addresses path escapes through:

- Parent-directory traversal such as `..`.
- Absolute paths outside the permitted base.
- Paths that share a textual prefix with the base but are not descendants.
- Symbolic links resolving outside the permitted base.

`LocalFileSystem` validates paths before opening local input or output streams. The validation is based on resolved path containment rather than string-prefix matching.

Path validation does not itself guarantee that a file exists or that the operating system will permit access. The filesystem operation determines whether a read or write succeeds.

### Security limitations

Path validation is **not an operating-system sandbox or an authorization mechanism**.

In particular:

- It does not eliminate time-of-check/time-of-use races if filesystem entries change between validation and opening.
- It cannot prevent access to resources for which the ETLRelay process already has excessive operating-system permissions.
- It does not prevent other processes from changing files, directory contents, or symbolic links.
- It does not enforce quotas, disk-space limits, or file-level access policies beyond the underlying operating system.

Run ETLRelay with only the filesystem permissions it requires. Prefer dedicated input/output directories and restrict modification of those directories by untrusted processes.

### File writes and overwrite behavior

`LocalFileSystem` creates output files using binary write mode and truncates existing files when they are opened for writing.

Parent directories are not created automatically.

ETLRelay does not provide atomic output replacement or automatic restoration of previous file contents. A failed write may leave an empty or partially written destination.

Backups, temporary-file replacement strategies, and application-level recovery remain the caller's responsibility when those guarantees are required.

See [Path Validator](architecture/path_validator.md), [Local Filesystem](architecture/local_filesystem.md), and [File Sink](architecture/file_sink.md).

## YAML configuration safety

ETLRelay reads configuration through `YamlReader`, which uses a safe YAML loader.

The reader rejects malformed documents, duplicate mapping keys, unsupported YAML object-construction tags, multiple documents where a single document is expected, non-mapping roots, and non-string root keys.

It does not use arbitrary Python object construction from YAML tags.

`ConfigValidator` validates the closed, versioned configuration schema. Schema version `1` requires the supported top-level structure and rejects unknown properties, unsupported component types, and unsupported configuration versions.

`PipelineBuilder` resolves explicit component registrations. Configuration does not support unrestricted Python imports, `eval`, or arbitrary Python expressions.

### Validation and preflight boundaries

Configuration loading, validation, component construction, and pipeline execution are separate responsibilities.

Validation rejects known configuration errors before normal pipeline execution. When building a configured pipeline, required SQL connection environment-variable references are checked before component factories are invoked.

These guarantees do **not** establish that:

- Referenced files exist, are readable, or contain valid runtime data.
- SQL connection URLs are valid or databases are reachable.
- Database users have the required permissions.
- SQL queries are authorized or return compatible data.
- Destination tables have compatible schemas or constraints.
- Custom components are trustworthy.
- All future runtime failures can be detected in advance.

The CLI `validate` command does not execute the configured data pipeline or write its output, but it is not a comprehensive security or runtime preflight.

Treat configuration from untrusted sources as untrusted input, even when it satisfies the YAML schema.

See [YAML Configuration](configuration.md) and [Configuration Loading](architecture/configuration-loading.md).

## SQL connection secrets

SQL configuration uses `connection_url_env` to name an environment variable containing a SQLAlchemy connection URL.

The configuration validator requires a valid environment-variable identifier rather than accepting a literal connection URL in that field.

During `PipelineBuilder.build()`, required environment-variable references are preflighted. Missing or empty values cause `PipelineBuildError` before component factories run.

`SqlEngineFactory` avoids including resolved connection URLs, credentials, or underlying driver exception messages in its own controlled error messages.

Do not commit connection URLs, passwords, API tokens, or private connection information to YAML files, examples, logs, or version control.

### Environment-variable limitations

Environment variables provide **secret indirection, not secure secret storage**.

ETLRelay does not provide credential encryption, rotation, access-control policy enforcement, or a secrets vault.

Applications and deployments must protect environment values, process permissions, operational logs, and diagnostic output. Use an appropriate external secrets-management or platform-native credential-injection mechanism where stronger controls are required.

Third-party libraries and application-provided logging handlers may disclose information outside ETLRelay's controlled diagnostics.

## SQL parameterization and authorization

`SqlSource` supports SQLAlchemy bound parameters for SQL values. Parameter values are sent as data rather than interpolated into the query string.

Use bound parameters for variable query values. Do not construct SQL by concatenating untrusted values into query text.

SQL identifiers, such as table names and column names, cannot be supplied as ordinary bound values. When dynamically constructing SQL identifiers, use trusted allowlists and appropriate SQLAlchemy APIs.

`SqlSink` uses SQLAlchemy statement construction and works with existing destination tables. It validates batch column names and uses SQLAlchemy's handling of SQL identifiers.

These behaviors reduce risks associated with unsafe SQL string construction, but they do not establish a SQL authorization policy.

`SqlSource` accepts caller-authored SQL query text. ETLRelay does not analyze queries to determine whether they are safe, read-only, efficient, or authorized.

The configured database account determines which operations the database permits. Apply least-privilege database credentials and review any SQL accepted from external users.

### Supported database scope

SQLite is the reference integration-test backend.

Other SQLAlchemy dialects require their corresponding drivers, suitable database permissions, and independent testing.

`SqlSink` provides append-only writes to existing tables. It does not implement table creation, schema migration, replacement, upserts, or database-level authorization controls.

## Error handling and logging

ETLRelay uses Python's standard `logging` module for operational diagnostics.

Built-in logging is intended to describe pipeline execution, validation, batch counts, component activity, and resource lifecycle events without routinely including record contents, SQL parameter values, complete connection URLs, or credentials.

The CLI defaults to `WARNING` and accepts `--log-level` to select a supported operational logging level. CLI logs are written to stderr, separately from normal command output.

When ETLRelay is used as a Python library, logging configuration belongs to the calling application. ETLRelay does not configure the application's root logger.

### Error propagation

Direct Python callers generally receive the original exceptions raised by the relevant components, including third-party exceptions where applicable.

The CLI separates usage errors, configuration and construction failures, and execution failures using documented exit codes:

| Exit code | Meaning |
|---|---|
| `0` | Successful execution |
| `1` | Unexpected CLI failure |
| `2` | Command usage error |
| `3` | Configuration or pipeline construction failure |
| `4` | Pipeline execution or cleanup failure |

For unexpected operational failures, the CLI avoids displaying raw third-party exception messages that could contain sensitive connection information or payloads.

Secondary iterator-cleanup failures are logged using controlled diagnostics rather than their exception messages.

### Redaction boundaries

These protections apply to **ETLRelay-controlled logging and CLI diagnostics**, not every possible diagnostic produced by a process.

They do not guarantee that all sensitive information is removed from:

- Exceptions observed by direct Python callers.
- Custom sources, processors, sinks, readers, or writers.
- Third-party database drivers and SQLAlchemy logging.
- Application-installed logging handlers.
- External monitoring and error-reporting services.
- User-supplied values intentionally included in configuration errors or application logs.

Avoid logging raw records, environment dumps, connection URLs, or SQL query payloads in production environments. Configure external library logging and diagnostic collection with the same care as ETLRelay's built-in logging.

See [Logging](logging.md) for operational levels, supported events, and further limitations.

## Resource ownership and cleanup

ETLRelay separates resources owned by a component from resources supplied by a caller.

### File resources

`FileSource` owns the input stream obtained from its configured `FileSystem`. `FileSink` owns the output stream it opens for writing.

Both use context-managed streams and release them on normal completion and relevant failures.

Readers and writers borrow streams provided by their callers; they do not close those streams.

When `Pipeline.run()` terminates, it attempts to close the active processing and source iterators when those iterators expose callable `close()` methods.

This includes early sink termination and failures during source iteration, processing, or writing.

Applications consuming a `FileSource` generator directly must close an active generator when they stop reading early and require deterministic cleanup.

### Failure precedence

If pipeline execution fails and iterator cleanup also fails, the original execution exception takes precedence.

Secondary cleanup failures are reported through controlled operational warnings.

If execution otherwise succeeds but required iterator cleanup fails, the first cleanup exception propagates.

The pipeline does not dispose of injected storage backends, database engines, or component instances merely because execution has completed.

### SQL resources

Direct Python `SqlSource` and `SqlSink` instances borrow the SQLAlchemy engine supplied by the caller. The caller remains responsible for engine disposal.

`SqlSource` manages the connection and query-result resources acquired during reading and releases them on completion or failure.

`SqlSink` uses an independent transaction for each nonempty batch. Failed transactions are rolled back through SQLAlchemy's transaction context, while previously committed batches remain committed.

Zero-row SQL sink batches are skipped before table reflection, column validation, or transaction creation.

For configuration-built pipelines, `PipelineBuilder` manages the shared `SqlEngineFactory` lifecycle. Call `builder.close()` after execution to release factory-owned engines, including when the pipeline fails.

Do not close a successfully built pipeline's required SQL resources before it runs.

See [Pipeline](architecture/pipeline.md) and [SQL Source and Sink](architecture/sql_source_and_sink.md).

## Empty data, schemas, and partial output

An entirely empty pipeline source produces no batches, so `Pipeline` does not invoke its sink.

A zero-row batch is different: it participates in processing and output-schema validation and is passed to the sink.

The first processed batch establishes the pipeline's expected output schema. Subsequent batches must match field names, field order, Arrow types, and nullability. Schema metadata differences are ignored.

Incompatible batches raise `ValueError` before being delivered to the sink.

The concrete writer or sink determines how valid zero-row batches are persisted:

- `CsvWriter` can write a header from a schema-bearing zero-row batch.
- `ParquetWriter` can write a valid empty Parquet file from a schema-bearing zero-row batch; an entirely empty iterable cannot establish its schema and raises `WriterError`.
- `SqlSink` skips zero-row batches without starting a transaction.

Pipeline execution is not atomic. A later validation or execution failure does not roll back earlier completed file writes or committed SQL batches.

## Dependency and distribution integrity

The v1.0.0 CI workflow includes:

- Lockfile consistency verification.
- Dependency vulnerability auditing.
- Installed dependency compatibility checks.
- Wheel and source-distribution builds.
- Distribution metadata and package-content verification.
- Separate clean-environment installation of the wheel and source distribution.
- Installed CLI and representative pipeline smoke tests.
- Compatibility verification across the documented Python/platform matrix.

These checks help identify packaging mistakes and known dependency vulnerabilities. They do not guarantee that dependencies are free of undiscovered vulnerabilities or that every operating-system configuration has been tested.

Applications deploying ETLRelay remain responsible for ongoing dependency maintenance and environment-specific security review.

## Current limitations and deferred risks

ETLRelay v1.0.0 does not provide:

- Operating-system-level filesystem sandboxing or elimination of path-validation races.
- A mechanism for safely executing arbitrary untrusted SQL or Python components.
- A credential vault, credential rotation, or infrastructure access-control management.
- Automatic sanitization of all third-party diagnostics.
- Atomic file replacement or automatic recovery of previous output.
- A transaction spanning multiple SQL batches or an entire pipeline.
- Automatic retries, distributed transactions, or idempotency guarantees.
- SQL schema migrations, table replacement, or upsert semantics.
- A general-purpose remote-storage security model.
- Comprehensive verification of all SQLAlchemy dialects and supported-platform combinations.

S3, HDFS, and other remote-storage implementations are outside the planned v1.0.0 scope. Additional integrations require their own security review and tests if introduced later.

These limitations should be evaluated explicitly when designing applications that use ETLRelay.

## Reporting vulnerabilities

Report suspected vulnerabilities privately using the repository's [Security Policy](https://github.com/apaquette/ETLRelay/blob/v1.0.1/SECURITY.md).

Do not include real credentials, private datasets, or production records in reports.
Parquet footer finalization follows primary-error precedence: a processing or
serialization failure is preserved when finalization also fails, and the
secondary warning identifies only the exception type. Failed finalization can
leave unreadable partial output. This is not an atomic-write guarantee.
