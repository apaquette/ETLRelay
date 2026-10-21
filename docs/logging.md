# Logging

ETLRelay uses Python's standard-library `logging` module to provide operational visibility into pipeline execution, configuration validation, file and SQL operations, and resource management.

Logging is configurable through the CLI or through standard Python logging configuration when ETLRelay is used as a library.

ETLRelay does not require an external logging dependency or introduce its own logging framework.

## CLI logging

Use the global `--log-level` option to control logging verbosity:

```bash
etlrelay --log-level info run pipeline.yaml
```

The option is available to CLI commands and must appear **before the command name**.

For example:

```bash
etlrelay --log-level debug run pipeline.yaml
etlrelay --log-level info validate pipeline.yaml
etlrelay --log-level warning run pipeline.yaml
```

The default logging level is `WARNING`.

### Supported logging levels

| Level | Description |
|---|---|
| `DEBUG` | Detailed operational events, including component lifecycle, processing progress, and resource management |
| `INFO` | High-level pipeline execution events, including start and successful completion |
| `WARNING` | Secondary or recoverable operational failures, such as resource cleanup failures |
| `ERROR` | Unexpected operational failures requiring attention |
| `CRITICAL` | Reserved for critical failures; ETLRelay does not currently define routine critical-level events |

Logging levels are case-insensitive.

An unsupported level is rejected as a CLI argument error.

### Example: INFO logging

Run a pipeline with informational logging:

```bash
etlrelay --log-level info run pipeline.yaml
```

A successful execution produces lifecycle messages similar to:

```text
INFO etlrelay.pipeline.pipeline: Pipeline execution started.
INFO etlrelay.pipeline.pipeline: Pipeline execution completed.
```

The CLI continues to report normal command results separately from log messages.

### Example: DEBUG logging

Use `DEBUG` to inspect additional operational activity:

```bash
etlrelay --log-level debug run pipeline.yaml
```

Depending on the configured pipeline, additional events can include:

```text
DEBUG etlrelay.config.loader: Configuration loading started.
DEBUG etlrelay.config.loader: Configuration validation completed.
DEBUG etlrelay.config.pipeline_builder: Pipeline components resolved.
DEBUG etlrelay.config.pipeline_builder: Pipeline construction completed.
DEBUG etlrelay.sources.file: File source read started.
DEBUG etlrelay.pipeline.pipeline: Processed batch 1: 100 rows.
DEBUG etlrelay.sources.file: File source read completed.
DEBUG etlrelay.sinks.file: File sink write completed.
```

These examples are illustrative. The events produced depend on the components used and whether execution completes successfully.

`DEBUG` provides more operational detail; it does not enable logging of data records, SQL parameters, or credentials.

### Standard output and standard error

ETLRelay separates normal command output from operational logs:

- **stdout** contains normal CLI output, such as successful command results.
- **stderr** contains logging messages and CLI error diagnostics.

This separation allows normal output to be redirected independently from diagnostics.

For example:

```bash
etlrelay --log-level info run pipeline.yaml > result.txt 2> pipeline.log
```

The command redirects normal output to `result.txt` and logs or error messages to `pipeline.log`.

ETLRelay's CLI logging configuration applies for the duration of the command. It does not permanently reconfigure the application's root logger.

## Python library logging

When ETLRelay is used directly through its Python API, the calling application controls logging configuration.

ETLRelay modules use named loggers under the `etlrelay` namespace, such as:

- `etlrelay.pipeline.pipeline`
- `etlrelay.sources.file`
- `etlrelay.sinks.file`
- `etlrelay.sources.sql`
- `etlrelay.sinks.sql`
- `etlrelay.config.loader`
- `etlrelay.config.pipeline_builder`
- `etlrelay.config.sql_engine_factory`

A standalone Python application can enable logging using the standard library:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

# Construct and execute an ETLRelay pipeline.
pipeline.run()
```

Here, `pipeline` represents a previously constructed ETLRelay `Pipeline`.

The application may instead configure the `etlrelay` logger specifically, use its existing logging handlers, or integrate logging with its own observability system.

Importing ETLRelay does not configure the application's root logger or force a particular logging destination or format.

## Operational events

### Pipeline execution

`Pipeline` emits:

| Level | Event | Meaning |
|---|---|---|
| `INFO` | `Pipeline execution started.` | Pipeline execution has begun |
| `INFO` | `Pipeline execution completed.` | Pipeline execution finished successfully |
| `DEBUG` | `Processed batch N: X rows.` | Batch N passed processor execution and pipeline schema validation |

An empty source can complete successfully without producing any batches.

A processed-batch event does **not** guarantee that the sink has committed or persisted that batch. Persistence is the responsibility of the sink.

If execution fails, the successful-completion event is not emitted.

### File sources and sinks

File components emit `DEBUG` lifecycle events:

| Component | Events |
|---|---|
| `FileSource` | Read started; read completed |
| `FileSink` | Write started; write completed |

Read completion is reported after normal iteration finishes and the source stream closes.

Write completion is reported after serialization succeeds and the output stream closes.

Failures do not produce successful-completion events. An early-closed source iterator does not report normal read completion.

### SQL sources and sinks

SQL components emit `DEBUG` events for successful operations.

`SqlSource` reports the number of rows successfully retrieved and converted into an ETLRelay batch.

`SqlSink` reports successful batch commits, including the number of inserted rows.

A SQL sink commit event is emitted **after the batch transaction commits successfully**. A transaction that fails or rolls back does not produce a successful-commit event.

Each nonempty SQL sink batch uses its own transaction. Successfully committed earlier batches remain committed if a later batch fails.

### Configuration and SQL resources

Configuration components emit `DEBUG` events when:

- Configuration loading starts.
- Configuration validation completes successfully.
- Pipeline component registrations resolve.
- Required SQL connection environment preflight succeeds.
- Pipeline construction completes successfully.

The SQL engine factory also emits events when owned engines are created, reused from its cache, or successfully disposed.

These events do not include resolved connection URLs or credentials.

## Errors and failure reporting

ETLRelay distinguishes operational logging from exception handling.

## Exception precedence and cleanup logging

ETLRelay distinguishes an operation's primary failure from secondary failures encountered while releasing resources.

When `Pipeline.run()` terminates, it attempts to close the active processing iterator and underlying source iterator when they expose callable `close()` methods.

If pipeline execution raises an exception, that exception remains primary even when iterator cleanup also fails. Secondary cleanup failures are reported using controlled warning messages that identify the exception type without including the original exception message.

If execution otherwise succeeds but iterator cleanup fails, the first cleanup exception propagates after cleanup has been attempted for the remaining closeable iterators.

Successful pipeline completion is not logged when required cleanup fails.

SQL sink batch-commit messages are emitted only after the corresponding transaction context has exited successfully. A failed commit must not be reported as successful.

These logging behaviors do not replace Python exception handling. Direct Python callers may still receive underlying exceptions containing information from external libraries. ETLRelay does not attempt to sanitize arbitrary third-party exceptions observed by calling applications.

### Python API

ETLRelay generally propagates underlying exceptions to Python callers rather than wrapping every failure in a generic framework exception.

Specific boundaries may translate errors where doing so provides a clearer contract. Examples include configuration validation, SQL environment preflight, and missing input-file handling.

Logging does not change the original exception or the caller's responsibility for handling it.

### CLI

The CLI reports validation, construction, execution, and cleanup failures using its established error-handling and exit-code conventions.

Unexpected failures can be logged with the failing operation and exception class without including the raw exception message.

If execution and resource cleanup both fail, the execution failure remains primary. Cleanup problems may be reported separately as warnings.

A failed operation is never logged as successfully completed.

For command syntax and exit-code details, consult the CLI help:

```bash
etlrelay --help
etlrelay run --help
etlrelay validate --help
```

## Sensitive information and logging

ETLRelay's built-in operational logging is designed to provide useful diagnostics without routinely exposing sensitive application data.

The standard logging events do not include:

- Complete data batches or record values.
- SQL query text or bound query parameters.
- Database connection URLs, passwords, or credentials.
- Access tokens or other secrets from SQL connection configuration.
- Full configuration payloads.
- Raw third-party exception messages or tracebacks.

Log messages focus on operational stages, component lifecycles, row counts, and exception types.

The `DEBUG` level does not disable these restrictions.

### Security boundaries and limitations

These protections apply to **logging and CLI output controlled by ETLRelay**. They are not a universal guarantee that no sensitive information can appear in application diagnostics.

Important limitations include:

- Direct Python callers receive underlying exceptions, which may contain database statements, parameter values, file paths, or driver-specific details.
- External libraries and database drivers may have independent logging configurations.
- Application-provided logging handlers and custom components may record additional information.
- Explicitly enabling SQLAlchemy statement or parameter logging can expose sensitive SQL data.
- ETLRelay does not attempt to sanitize arbitrary third-party exception messages through a general-purpose redaction framework.

Applications remain responsible for protecting log files, configuring appropriate log retention and access controls, and managing database credentials securely.

For additional information about security responsibilities and limitations, see [Security](security.md).

## Troubleshooting

### No INFO messages appear

The default logging level is `WARNING`. Enable informational logging explicitly:

```bash
etlrelay --log-level info run pipeline.yaml
```

### More operational detail is needed

Use `DEBUG`:

```bash
etlrelay --log-level debug run pipeline.yaml
```

This provides additional component and batch-level diagnostics without enabling payload logging.

### A pipeline fails without a detailed traceback

The CLI intentionally avoids printing potentially sensitive raw exception details.

For application-level investigation, use ETLRelay's Python API where appropriate and handle the underlying exception within your application's own error-reporting and security policy.

### SQL operations are not visible in logs

ETLRelay's SQL operational events generally use `DEBUG`. Enable that level to see successful source reads, batch commits, and engine lifecycle events.

ETLRelay does not automatically enable SQLAlchemy's SQL statement logging.

### Duplicate logging messages appear in a Python application

Check whether the application has configured multiple handlers for the same logger or has allowed messages to propagate to handlers higher in the logger hierarchy.

The ETLRelay library does not install its own application-wide logging handlers.