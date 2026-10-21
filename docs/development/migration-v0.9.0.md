# Migration to v0.9.0

This page describes changes from v0.8.0 to v0.9.0. Install
`etlrelay==0.9.0` before updating and testing the Python imports below.

## Rename the tabular protocols

Update imports and type annotations:

| Before | After |
| --- | --- |
| `from etlrelay.core import Reader` | `from etlrelay.core import TabularReader` |
| `from etlrelay.core import Writer` | `from etlrelay.core import TabularWriter` |
| `from etlrelay.core.reader import Reader` | `from etlrelay.core.reader import TabularReader` |
| `from etlrelay.core.writer import Writer` | `from etlrelay.core.writer import TabularWriter` |

There are no legacy class aliases. Module paths remain `core.reader` and
`core.writer`. Concrete `CsvReader`, `ParquetReader`, `CsvWriter`, and
`ParquetWriter` names and constructor signatures are unchanged.

The contracts remain:

```python
from collections.abc import Iterable
from typing import BinaryIO

from etlrelay.core import Batch, TabularReader, TabularWriter


def copy_batches(reader: TabularReader, writer: TabularWriter,
                 source: BinaryIO, destination: BinaryIO) -> None:
    batches: Iterable[Batch] = reader.read(source)
    writer.write(batches, destination)
```

Both streams are borrowed and must remain open while batches are consumed.
The caller closes them. File sources/sinks own streams they open themselves.

`KeyValueReader` remains the separate mapping-document protocol, returning one
`Mapping[str, Any]`. It is used by `ConfigLoader`; it does not produce tabular
batches or row-record sequences. `KeyValueWriter` and generic record conversion
remain deferred. No replacement configuration reader is required.

## Account for corrected failures

- Invalid YAML root shapes now raise `YamlDocumentError`, a `ValueError`
  subclass. Existing `except ValueError` handlers continue to work. It is
  available from `etlrelay.readers` and `etlrelay.readers.yaml`.
- CLI `run` and `validate` classify these document errors as configuration
  failures with exit code `3`, rather than unexpected-error code `1`.
- `SelectColumns` raises `ValueError` for ambiguous requested field names,
  replacing the underlying Arrow `KeyError` previously exposed in that case.
- `RenameColumns` rejects duplicate final names even when duplicate fields
  originated in the input batch. Correct the input names or selection first.
- If upstream processing/serialization and Parquet finalization both fail, the
  original error is preserved. Secondary finalization failures are logged by
  type without their messages. Finalization-only failures still propagate.

File output can still be partial or unreadable after a failed run. SQL output
still commits per nonempty batch; rerunning may append duplicates. These fixes
add no atomic replacement, retries, or pipeline-wide rollback.

## Dependencies and configuration

Polars is no longer a runtime dependency because the frozen implementation uses
PyArrow. Applications using Polars independently must declare it themselves.

YAML schema version `1`, supported component names, CLI commands, and the
remaining exit codes are unchanged. `validate` parses and checks the schema;
SQL environment resolution occurs during `run` construction. No YAML migration
or new storage integration is required.

Use the [API reference](../api-reference.md), [failure matrix](failure-matrix.md),
and [packaging record](packaging-verification.md) for detailed contracts and
verification evidence.
