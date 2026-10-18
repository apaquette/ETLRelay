# Getting Started

ETLRelay 0.6.0 supports both direct Python composition and versioned YAML configuration. This guide starts with YAML—the new declarative interface—and then explains where to go for the direct component API.

## Requirements

- Python 3.12 or newer.
- ETLRelay 0.6.0.
- A local filesystem directory where the example data and outputs can be stored.

For the full runnable examples, clone the repository and install the package in an environment using the repository's supported Python setup:

```bash
git clone https://github.com/apaquette/ETLRelay.git
cd ETLRelay
python -m pip install -e .
```

The examples are kept under `examples/configuration/` so that their YAML files, preparation script, and runner can be used together. If you are using the published package rather than a checkout, use the package version and Python environment appropriate to your installation, and obtain the examples from the v0.6.0 repository tag.

## Prepare the demonstration data

Run the preparation script from the repository root:

```bash
python examples/configuration/prepare_demo_data.py
```

It creates a small CSV input file, a corresponding Parquet input file, and source/target SQLite databases in `examples/configuration/data/`. The target table is deliberately created before the SQL sink runs because `SqlSink` appends to an existing table; it does not create or migrate tables.

The sample input contains `id`, `amount`, and `state`. The YAML processors select `id` and `amount`, keep rows where `amount >= 0`, and rename `id` to `record_id`.

## Run a YAML pipeline

The runner loads the YAML document through `ConfigLoader`, validates it using the default component catalog, constructs the pipeline with `PipelineBuilder`, executes it, and closes the shared SQL engine factory in a `finally` block.

Run a CSV-to-CSV pipeline:

```bash
python examples/configuration/run.py examples/configuration/csv_to_csv.yaml
```

Run a CSV-to-Parquet pipeline:

```bash
python examples/configuration/run.py examples/configuration/csv_to_parquet.yaml
```

The runner accepts any of the nine YAML examples in `examples/configuration/`: four file-to-file format pairs, two file-to-SQL pairs, two SQL-to-file pairs, and one SQL-to-SQL pair. Outputs are written beneath `examples/configuration/data/`.

For SQL examples, configure the demo database URLs in the process environment:

```bash
export ETLRELAY_SOURCE_DATABASE_URL="sqlite:///examples/configuration/data/source.db"
export ETLRELAY_SINK_DATABASE_URL="sqlite:///examples/configuration/data/sink.db"
```

Then run, for example:

```bash
python examples/configuration/run.py examples/configuration/sql_to_sql.yaml
```

Each SQL configuration references the variable name in its `connection_url_env` field. The YAML file never contains the resolved URL. These demo URLs are local and contain no credentials; do not put credential-bearing connection URLs or passwords into configuration files.

## Understand the YAML pipeline

A typical file pipeline has four required top-level properties: `version`, `source`, `processors`, and `sink`.

```yaml
version: 1

source:
  type: file
  path: examples/configuration/data/input.csv
  format: csv
  storage:
    type: local
    base_path: .

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
  path: examples/configuration/data/output.csv
  format: csv
  storage:
    type: local
    base_path: .
```

The `version` property is the configuration schema version, currently integer `1`; it is independent of the Python package version `0.6.0`. A `processors` list is required, but `processors: []` is valid and passes batches through without transformations.

Processor order matters: `select_columns` drops `state`, `filter_rows` removes negative amounts, and `rename_columns` changes the retained `id` field to `record_id`. Formats are explicit; ETLRelay does not infer them from file extensions.

## Validation and errors

The loader's validation stage checks the configuration structure, required fields, schema version, component names, and property types. Invalid configuration is rejected before source/sink operations and pipeline execution.

For example:

- An unknown property such as `sink.destination` is rejected.
- An unsupported file format is rejected using the format registry's reading/writing capability.
- A filter operator outside `==`, `!=`, `<`, `<=`, `>`, `>=` is rejected.
- A missing or empty SQL connection environment variable fails during build-time preflight, before ETL component factories are invoked.

Schema validation does not prove that the named input file exists, that a selected column is present in the runtime schema, that SQL will succeed, or that the destination table is compatible. These are runtime conditions. See [YAML Configuration](configuration.md) for the full schema and [Configuration Validation Architecture](architecture/configuration-validation.md) for validation boundaries.

## Programmatic composition remains supported

The YAML interface is additive; direct Python construction remains available. This is still supported:

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

base = Path("data").resolve()
storage = LocalFileSystem(path_validator=PathValidator(base_path=base))
pipeline = Pipeline(
    source=FileSource(path="input.csv", storage=storage, reader=CsvReader()),
    processors=[
        SelectColumns(columns=["name", "age"]),
        RenameColumns(mapping={"name": "customer_name"}),
        FilterRows(column="age", operator=">=", value=18),
    ],
    sink=FileSink(path="output.csv", storage=storage, writer=CsvWriter()),
)
pipeline.run()
```

For this direct API example, `data/input.csv` must exist and the output is `data/output.csv`. Engine lifecycle for direct `SqlSource`/`SqlSink` components remains caller-owned; the managed engine lifecycle described above applies to configuration-built pipelines using the shared `SqlEngineFactory`.

## More details

- [YAML Configuration](configuration.md) — versioned schema, component matrix, secret handling, and errors.
- [Core Concepts](concepts.md) — batches, schema behavior, empty inputs, and synchronous execution.
- [API Reference](api-reference.md) — public interfaces and classes.
- [Configuration Loading Architecture](architecture/configuration-loading.md) — reader/loader boundaries.
- [Component Registry Architecture](architecture/component-registry.md) — registries, factories, and default catalog.
- [Security](security.md) — path containment and SQL credential handling.
