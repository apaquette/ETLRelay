# Command-Line Interface Reference

ETLRelay provides a command-line interface (CLI) for validating and executing supported YAML pipeline configurations. Install ETLRelay into the Python environment where you intend to run it, then invoke the `etlrelay` command from a terminal.

```bash
python -m pip install etlrelay==0.8.0
etlrelay --help
etlrelay version
```

The package supports CPython 3.12–3.14 (`>=3.12,<3.15`). See [Getting Started](getting-started.md) for installation and a complete local CSV example, and [YAML Configuration](configuration.md) for the supported schema and component properties.

## General usage

```text
etlrelay [OPTIONS] COMMAND [ARGS]...
```

`-h` and `--help` display help. Run `etlrelay --help` for the command list or append `--help` to a command to inspect its arguments and options. Running `etlrelay` without a command also displays root help.

## Commands

### `etlrelay run PIPELINE`

Load, validate, build, and execute the pipeline defined in the YAML file at `PIPELINE`.

```bash
etlrelay run pipeline.yaml
```

The configuration must describe supported source, processor, and sink components. Relative filesystem paths should be configured deliberately; use the same working directory assumed by the configuration's local storage `base_path`.

On success, the command prints a confirmation to standard output, for example:

```text
Pipeline completed: pipeline.yaml
```

A configuration loading or validation failure exits with code `3`. An unexpected internal or pipeline-construction error exits with code `1`. A source, processor, sink, or runtime-resource-cleanup failure exits with code `4`.

### `etlrelay validate PIPELINE`

Parse and validate a YAML pipeline configuration without building or executing the pipeline.

```bash
etlrelay validate pipeline.yaml
```

On success, the command prints a confirmation to standard output:

```text
Pipeline configuration is valid: pipeline.yaml
```

Validation checks configuration syntax and the supported schema. It does **not** prove that an input file exists, that runtime data contains every referenced column, that a database connection will succeed, or that the output destination is writable. Those conditions may only become apparent when the pipeline is built or run.

Configuration, YAML parsing, file-access, and validation failures exit with code `3`. Unexpected internal failures exit with code `1`.

### `etlrelay version`

Print the installed package version from distribution metadata.

```bash
etlrelay version
```

Example output:

```text
etlrelay 0.7.0
```

If the installed package version cannot be determined from metadata, the command exits with code `1` and writes a diagnostic to standard error.

### `etlrelay help [COMMAND]`

Display general help or help for a named command.

```bash
etlrelay help
etlrelay help run
etlrelay help validate
```

An unknown help target is a usage error and exits with code `2`. The normal `--help` option is also supported, for example `etlrelay run --help`.

## Exit codes

The CLI uses the following process exit codes:

| Code | Meaning | Typical examples |
|---:|---|---|
| `0` | Success | Help/version displayed; validation passes; pipeline completes |
| `1` | Unexpected internal error | Unexpected configuration-loading or pipeline-construction failure; package version metadata unavailable |
| `2` | Command usage error | Missing required argument, invalid invocation, or unknown command supplied to `etlrelay help` |
| `3` | Configuration or build failure | Malformed YAML, invalid configuration, inaccessible configuration file, or `PipelineBuildError` |
| `4` | Runtime execution or cleanup failure | Source read fails, a processor fails, a sink write fails, or builder cleanup fails |

Use the exit code for automation rather than parsing the diagnostic text.

## Standard output and standard error

- **Standard output (`stdout`)** contains help, version information, and successful command confirmations.
- **Standard error (`stderr`)** contains usage, configuration, validation, execution, and unexpected-error diagnostics.
- Successful commands return exit code `0`; failures return the code associated with the failure category above.
- Runtime execution diagnostics include the exception type and a general troubleshooting hint, but omit the underlying runtime exception message and traceback.
- Configuration-validator and pipeline-builder diagnostics may include their own error details to identify the invalid configuration. Do not place credentials or other secrets in YAML values or error messages; reference SQL connection URLs through environment-variable names as described in [YAML Configuration](configuration.md).

The CLI's error presentation is intended to be useful without printing runtime payloads. It is not a substitute for controlling access to process environments, configuration files, or application logs.

## Example: local CSV pipeline

Create `input.csv` in a working directory:

```csv
id,amount,state
1,10,ready
2,-2,skip
3,5,ready
```

Create `pipeline.yaml` in the same directory:

```yaml
version: 1

source:
  type: file
  path: input.csv
  format: csv
  storage:
    type: local
    base_path: .

processors:
  - type: select_columns
    columns: [id, amount]
  - type: filter_rows
    column: amount
    operator: ">"
    value: 0
  - type: rename_columns
    mapping:
      id: record_id

sink:
  type: file
  path: output.csv
  format: csv
  storage:
    type: local
    base_path: .
```

From that working directory, validate and run the pipeline:

```bash
etlrelay validate pipeline.yaml
etlrelay run pipeline.yaml
```

The resulting `output.csv` contains the positive-amount rows with `id` renamed to `record_id`. The configured processor list runs in order. The schema and available component properties are documented in [YAML Configuration](configuration.md).

## Automation notes

- Use `etlrelay validate pipeline.yaml` before scheduling or invoking `etlrelay run pipeline.yaml`, but remember that validation cannot guarantee runtime resources will be available.
- Check the documented process exit code to decide whether an automated job succeeded.
- Keep credentials out of YAML configuration and diagnostic text. Use environment-variable references for SQL connection URLs.
- The CLI is synchronous. It does not provide scheduling, retries, background jobs, or a daemon.

## YAML document-shape failures

An empty document, a non-mapping root, or a root with non-string keys is a
configuration failure. Both `validate` and `run` return exit code `3` and
report the required document shape without echoing document contents.

`validate` does not construct runtime components or resolve SQL connection
environment variables. SQL environment preflight occurs during `run` when
`PipelineBuilder` constructs the pipeline.
