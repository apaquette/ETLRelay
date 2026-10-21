# Getting Started

This guide covers ETLRelay v1.0.0. Applications upgrading from v0.9.0 need
no Python or YAML changes. For older versions, see the
[v0.9.0 migration guide](development/migration-v0.9.0.md).

## Install in a clean environment

Use CPython 3.12, 3.13, or 3.14. Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Linux/macOS, run `source .venv/bin/activate`. On Windows PowerShell, run
`.venv\Scripts\Activate.ps1`. Run the remaining commands in that environment.

Install the release and inspect its commands:

```bash
python -m pip install etlrelay==1.0.0
etlrelay --help
etlrelay version
```

`etlrelay version` reports `etlrelay 1.0.0`. To verify a local release build
before publication, run `uv build` in the checkout and install its archive in
the clean environment instead:

```bash
python -m pip install /absolute/path/to/ETLRelay/dist/etlrelay-1.0.0-py3-none-any.whl
```

## Run a self-contained CSV pipeline

In a writable working directory, save this as `input.csv`:

```csv
id,amount,state
1,10,ready
2,-2,skip
3,5,ready
```

Save this as `pipeline.yaml` in the same directory:

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

Validate, then execute from that directory:

```bash
etlrelay validate pipeline.yaml
etlrelay run pipeline.yaml
```

`validate` parses and checks the document/schema. It does not build runtime
components, resolve SQL connection values, or run data processing. Successful
validation does not prove that input data or output resources will work.

A successful `run` prints `Pipeline completed: pipeline.yaml` and creates:

```text
"record_id","amount"
1,10
3,5
```

All four root fields are required. `processors: []` is valid. The integer
`version: 1` is the configuration schema version, independent of the package
version. Formats are selected explicitly rather than inferred from extensions.

## Compose the equivalent pipeline in Python

Save this as `pipeline.py` beside the same `input.csv`:

```python
from pathlib import Path

from etlrelay.pipeline import Pipeline
from etlrelay.processors import FilterRows, RenameColumns, SelectColumns
from etlrelay.readers import CsvReader
from etlrelay.security import PathValidator
from etlrelay.sinks import FileSink
from etlrelay.sources import FileSource
from etlrelay.storage import LocalFileSystem
from etlrelay.writers import CsvWriter

storage = LocalFileSystem(PathValidator(Path.cwd()))
Pipeline(
    FileSource("input.csv", storage, CsvReader()),
    [
        SelectColumns(["id", "amount"]),
        FilterRows("amount", ">", 0),
        RenameColumns({"id": "record_id"}),
    ],
    FileSink("python-output.csv", storage, CsvWriter()),
).run()
```

Run `python pipeline.py`. `python-output.csv` contains the same records and
columns as `output.csv`.

A pipeline entirely without batches leaves its destination untouched. Opening a
local output otherwise truncates existing contents; failures may leave partial
output. SQL sinks append to existing tables using one transaction per nonempty
batch. Neither path provides pipeline-wide rollback.

## Run the repository examples

Obtain the `examples/` directory from the `v1.0.0` release tag.
A published package should instead use examples from its matching release tag.
Examples are repository files, not a guaranteed wheel payload.

From a repository root or a working directory containing a copied `examples/`:

```bash
python examples/copy_csv.py
python examples/transform_csv.py
python examples/parquet_pipeline.py
python examples/sqlite_pipeline.py
python examples/custom_processor.py
python examples/configuration/prepare_demo_data.py
etlrelay run examples/configuration/csv_to_csv.yaml
```

The preparation script recreates demonstration tables. It is for disposable demo
resources, not an application migration tool. See the
[YAML examples instructions](https://github.com/apaquette/ETLRelay/tree/v1.0.0/examples/configuration)
for all nine configurations, SQL environment setup, expected results, and reset
behavior.

The SQL examples use local SQLite URLs without credentials. Real SQL components
reference environment-variable names, not literal URLs in YAML. The destination
table must already exist. Missing or empty variables fail during `run` build
preflight; `validate` does not resolve them.

## Troubleshoot the first run

| Symptom | Check |
| --- | --- |
| Command is unavailable | Activate the environment where the archive was installed; inspect `etlrelay version`. |
| Exit 2 | Check command syntax and required arguments with `etlrelay help run`. |
| Exit 3 | Check YAML shape/schema, supported fields, configuration-file access, and build-time SQL environment references. |
| Exit 4 | Check input parsing, selected columns/types, filesystem access, existing SQL tables, and cleanup. Earlier output may remain. |
| Exit 1 | An unexpected internal failure occurred; reproduce with synthetic data and report the version/commit and operation. |
| A relative path cannot be found | Paths use the process working directory and configured storage base, not the YAML file's directory. |
| Diagnostics need more context | Run `etlrelay --log-level debug run pipeline.yaml`; logs go to stderr and omit raw runtime exception details. |

See [Configuration](configuration.md), [CLI Reference](cli-reference.md),
[Logging](logging.md), and [Security](security.md) for precise contracts and
[Migration to v0.9.0](development/migration-v0.9.0.md) for API changes.
