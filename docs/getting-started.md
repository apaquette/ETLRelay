# Getting Started

This guide demonstrates copying a local CSV file through ETLRelay's source, pipeline, and sink components. It uses the initial programmatic API; YAML configuration and a CLI are not included in the planned `0.1.0` release.

## Requirements

- Python 3.12 or newer.
- A CSV input file.
- ETLRelay installed in the environment.

Once the package is published, install it with:

```bash
python -m pip install etlrelay
```

Before publication, run from a repository checkout using the project's documented development setup.

## Prepare an input file

Create a working directory and place a CSV file at `data/input.csv`. For example:

```csv
name,age
Alice,30
Bob,25
```

The output will be written to `data/output.csv`.

## Run a pipeline

```python
from pathlib import Path

from etlrelay.pipeline.pipeline import Pipeline
from etlrelay.readers.csv import CsvReader
from etlrelay.security.path import PathValidator
from etlrelay.sinks.file import FileSink
from etlrelay.sources.file import FileSource
from etlrelay.storage.local import LocalFileSystem
from etlrelay.writers.csv import CsvWriter


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
    processors=[],
    sink=sink,
)
pipeline.run()
```

The example uses an empty processor sequence, so the pipeline passes the input batches through unchanged. A processor can be added when a transformation is required.

The storage implementation opens the file streams, the reader parses CSV data into a `Batch`, and the writer serializes batches to CSV. The pipeline coordinates the flow without knowing the storage or format details.

> Before treating this example as the release's supported quick start, run it against the actual installed `0.1.0` wheel and ensure its imports and constructor signatures match the implementation.
