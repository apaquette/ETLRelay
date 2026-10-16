# Getting Started

This guide demonstrates a local CSV transformation pipeline and shows how to switch the same composition model to Parquet. Both formats use the same file source/sink, storage, and processor abstractions.

The example selects columns, renames a column, and filters rows before writing the results to a new CSV file.

## Requirements

- Python 3.12 or newer.
- ETLRelay installed in your environment.
- A local CSV input file.

Install ETLRelay from the package repository:

```bash
python -m pip install etlrelay
```

## Prepare the input file

Create a `data` directory and save the following as `data/input.csv`:

```csv
name,age,department
Alice,17,Engineering
Bob,25,Data
Charlie,18,QA
Diana,16,Data
Evan,42,Engineering
```

The pipeline will write its output to `data/output.csv`.

## Build and run a pipeline

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


data_dir = Path("data").resolve()

storage = LocalFileSystem(
    path_validator=PathValidator(base_path=data_dir),
)

source = FileSource(
    path="input.csv",
    storage=storage,
    reader=CsvReader(),
)

sink = FileSink(
    path="output.csv",
    storage=storage,
    writer=CsvWriter(),
)

pipeline = Pipeline(
    source=source,
    processors=[
        SelectColumns(columns=["name", "age"]),
        RenameColumns(mapping={"name": "customer_name"}),
        FilterRows(column="age", operator=">=", value=18),
    ],
    sink=sink,
)

pipeline.run()
```

Run the script from the directory containing `data/`. The directory and input file must already exist.

## Understand the transformations

The processors execute in their configured order:

1. `SelectColumns` retains `name` and `age`, dropping `department`.
2. `RenameColumns` changes `name` to `customer_name`.
3. `FilterRows` retains rows where `age >= 18`.

Each processor receives the previous processor's output. The pipeline then passes the processed batches to the CSV writer and sink.

## Expected output

After running the pipeline, `data/output.csv` contains:

```csv
"customer_name","age"
"Bob",25
"Charlie",18
"Evan",42
```

The output preserves the order of the matching input rows and contains only the selected and renamed columns.

For more details on batch behavior, empty inputs, and output schema compatibility, see [Core Concepts](concepts.md). For constructor parameters and validation behavior, see the [API Reference](api-reference.md).


## Using Parquet

The same composition model supports Parquet. Select the format explicitly by supplying `ParquetReader()` to `FileSource` and `ParquetWriter()` to `FileSink`; ETLRelay does not infer the format from a filename extension. The executable example at [`examples/parquet_pipeline.py`](https://github.com/apaquette/ETLRelay/blob/v0.3.0/examples/parquet_pipeline.py) creates a small input file, applies the same select/rename/filter processors as the CSV example, and writes `data/output.parquet`.

The central composition looks like this:

```python
from etlrelay.readers import ParquetReader
from etlrelay.sources import FileSource
from etlrelay.sinks import FileSink
from etlrelay.writers import ParquetWriter

source = FileSource(
    path="input.parquet",
    storage=storage,
    reader=ParquetReader(),
)
sink = FileSink(
    path="output.parquet",
    storage=storage,
    writer=ParquetWriter(),
)
```

Parquet retains its supported schema and data types, while CSV is text-based and infers types when read. A `ParquetWriter` requires at least one batch to establish its schema: an empty iterable raises `WriterError`. A zero-row `Batch` with a schema is valid and creates a schema-bearing Parquet file. `ParquetReader` requires a seekable binary stream; the reader/writer contracts are stream-based and leave stream lifecycle management to the component that opened the stream. See [Reader and Writer](architecture/reader_and_writer.md) and [Core Concepts](concepts.md) for format-specific behavior and limitations.


## Using SQL with SQLite

The following small example creates an in-memory SQLite database, reads selected orders with a **bound query parameter**, removes an unused column, and appends the processed rows to an existing table. It requires SQLAlchemy and the project's declared dependencies; it uses no credentials or external database service.

The complete runnable version is [`examples/sqlite_pipeline.py`](https://github.com/apaquette/ETLRelay/blob/v0.5.0/examples/sqlite_pipeline.py).

```python
from sqlalchemy import Column, Float, Integer, MetaData, String, Table, create_engine

from etlrelay.pipeline import Pipeline
from etlrelay.processors import SelectColumns
from etlrelay.sinks import SqlSink
from etlrelay.sources import SqlSource

engine = create_engine("sqlite://")  # in-memory SQLite; no credentials
metadata = MetaData()

orders = Table(
    "orders", metadata,
    Column("id", Integer, primary_key=True),
    Column("customer", String, nullable=False),
    Column("status", String, nullable=False),
    Column("total", Float, nullable=False),
)
Table(
    "processed_orders", metadata,
    Column("id", Integer, primary_key=True),
    Column("customer", String, nullable=False),
    Column("total", Float, nullable=False),
)
metadata.create_all(engine)  # setup for this demo; SqlSink does not create tables

with engine.begin() as connection:
    connection.execute(orders.insert(), [
        {"id": 1, "customer": "Avery", "status": "ready", "total": 18.5},
        {"id": 2, "customer": "Riley", "status": "held", "total": 27.0},
    ])

pipeline = Pipeline(
    source=SqlSource(
        engine,
        "SELECT id, customer, status, total FROM orders WHERE status = :status",
        parameters={"status": "ready"},
    ),
    processors=[SelectColumns(columns=["id", "customer", "total"])],
    sink=SqlSink(engine, "processed_orders"),
)
pipeline.run()

# The engine belongs to the application. Dispose it when all DB work is done.
engine.dispose()
```

Important contract details:

- `SqlSource` binds query **values** with `parameters`; do not interpolate untrusted values into SQL text. Bind parameters cannot stand in for table/column identifiers.
- `SqlSink` is append-only and requires the destination table to exist with compatible columns. It does not implement `replace`, ORM models, or schema migrations.
- Each non-empty batch is committed in its own transaction. Earlier batches remain committed if a later batch fails.
- The application owns the SQLAlchemy engine. ETLRelay closes connections/results it opens but does not dispose the engine.
- SQLite is the continuously tested reference backend; other SQLAlchemy dialects need the matching driver and independent verification.

See [SQL source and sink architecture](architecture/sql_source_and_sink.md) and the [API Reference](api-reference.md) for full behavior and limitations.

