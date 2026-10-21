# FileSink

## Purpose

`FileSink` is a sink component responsible for writing ETLRelay batches to a configured file resource.

It composes two independent components:

* `FileSystem`, which provides a writable binary stream for the destination.
* `TabularWriter`, which serializes an iterable of `Batch` objects into the supplied stream.

`FileSink` does not depend on a particular storage implementation or file format. The current implementation combines `LocalFileSystem` with `CsvWriter` or `ParquetWriter` without changing the sink implementation.

## Class Diagram

```mermaid
classDiagram
    class Sink {
        <<protocol>>
        +write(batches: Iterable~Batch~) None
    }

    class FileSink {
        -path: str
        -storage: FileSystem
        -writer: TabularWriter
        +write(batches: Iterable~Batch~) None
    }

    class FileSystem {
        <<protocol>>
        +open_write(path: str) BinaryIO
    }

    class TabularWriter {
        <<protocol>>
        +write(batches: Iterable~Batch~, stream: BinaryIO) None
    }

    class LocalFileSystem {
        +open_write(path: str) BinaryIO
    }

    class CsvWriter {
        +write(batches: Iterable~Batch~, stream: BinaryIO) None
    }

    class ParquetWriter {
        +write(batches: Iterable~Batch~, stream: BinaryIO) None
    }

    class PathValidator {
        +validate(path: Path | str) Path
    }

    class Batch

    Sink <|.. FileSink
    FileSystem <|.. LocalFileSystem
    TabularWriter <|.. CsvWriter
    TabularWriter <|.. ParquetWriter

    FileSink --> FileSystem : uses
    FileSink --> TabularWriter : uses

    LocalFileSystem --> PathValidator : validates paths with

    TabularWriter --> Batch : consumes
```

## Responsibilities

### FileSink

`FileSink` is responsible for:

* Storing the configured destination path.
* Opening the destination through the supplied `FileSystem`.
* Passing the iterable of batches and writable stream to the supplied `TabularWriter`.
* Opening the destination once per write operation rather than once per batch.
* Ensuring the stream is closed after writing, including when serialization fails.
* Implementing the `Sink` protocol.

`FileSink` is **not** responsible for:

* Implementing filesystem operations.
* Validating local filesystem path containment.
* Serializing CSV, Parquet, or other file formats.
* Transforming or constructing `Batch` objects.
* Selecting a storage backend or writer implementation.
* Orchestrating pipeline execution.
* Defining format-specific behavior for empty batches.
* Implementing application-level logging.

### FileSystem

`FileSystem` defines the storage contract used to open the destination for writing.

Its implementations handle storage-specific behavior, including resource access, opening writable streams, and any applicable path validation.

`FileSink` depends on the protocol rather than directly on `LocalFileSystem`.

### TabularWriter

`TabularWriter` defines the contract for serializing an iterable of `Batch` objects into a binary stream.

Its implementations handle format-specific serialization. The current built-in writers are `CsvWriter` and `ParquetWriter`.

The writer is responsible for processing the iterable according to its contract, including handling empty batches and determining how multiple batches are represented in one output resource. Format-specific constraints remain the writer's responsibility; for example, `ParquetWriter` requires a first batch to establish the output schema, so an empty iterable is not equivalent to a zero-row batch with a schema.

`FileSink` does not need to know how the writer serializes the batches.

## Dependency Relationship

```text
Sink
 ▲
 │ implements
 │
FileSink
 ├── FileSystem
 │      └── LocalFileSystem
 │              └── PathValidator
 │
 └── TabularWriter
        ├── CsvWriter
        └── ParquetWriter
```

`FileSink` depends on the `FileSystem` and `TabularWriter` protocols, not their concrete implementations.

Current file-based combinations use local storage with one of the built-in formats:

```text
LocalFileSystem + CsvWriter
LocalFileSystem + ParquetWriter
```

Remote storage backends such as S3 and HDFS are not implemented in v0.6.0 and are not part of the planned v1.0.0 scope. Additional storage implementations may be reviewed after v1.0.0 if concrete requirements justify them; no particular backend or release date is promised.

## Data Flow

The sink coordinates the following operations:

```text
FileSink.write(batches)
          │
          ▼
FileSystem.open_write(path)
          │
          ▼
    BinaryIO stream
          │
          ▼
TabularWriter.write(batches, stream)
          │
          ▼
   Serialized file data
          │
          ▼
       filesystem
```

The storage implementation provides the writable stream. The writer serializes the iterable of batches into that stream.

The stream is managed using a context manager so that it is closed after writing, including when serialization raises an exception.

A single call to `FileSink.write()` represents one output operation for the configured destination. All batches supplied in that call are handled by the writer through the same stream.

The sink does not buffer the entire iterable or independently iterate over it before passing it to the writer.

## Interface

### FileSink

```python
from collections.abc import Iterable

from etlrelay.core import Batch, TabularWriter
from etlrelay.storage import FileSystem


class FileSink:
    def __init__(
        self,
        path: str,
        storage: FileSystem,
        writer: TabularWriter,
    ) -> None:
        ...

    def write(self, batches: Iterable[Batch]) -> None:
        ...
```

## Contract

| Operation | Expected behavior |
| --- | --- |
| Construct with path, storage, and writer | Stores the supplied dependencies and destination path |
| Write an iterable of batches | Delegates serialization to the supplied writer |
| Write multiple batches | Passes all batches through a single output stream |
| Write an empty iterable | Delegates empty-input handling to the writer |
| Write an iterable containing empty batches | Delegates empty-batch handling to the writer |
| Write to a new valid local destination | Creates the destination file when the parent directory exists and access is permitted |
| Write to an invalid local path | Propagates the path-validation error from local storage |
| Write when storage access fails | Propagates the underlying storage error |
| Write when serialization fails | Propagates the writer's exception |
| Complete or fail a write | Closes the opened stream |
| Supply another storage implementation | Works without modifying `FileSink`, provided it satisfies `FileSystem` and its behavioral contract |
| Supply another writer implementation | Works without modifying `FileSink`, provided it satisfies `TabularWriter` and its behavioral contract |

Exceptions are propagated rather than wrapped in a new `FileSink` exception hierarchy.

For the current local filesystem implementation, opening a destination for writing uses binary write mode. An existing destination is therefore truncated, while a new destination is created if its parent directory exists and filesystem access is permitted. Parent directories are not created automatically.

`FileSink` closes the stream returned by `FileSystem.open_write()` on
successful completion and on serialization failure.

With `LocalFileSystem`, opening an existing output truncates it
immediately. A failure may leave an empty or partially written file;
the previous contents are not restored.

`FileSink` does not provide atomic replacement or rollback. It delegates
empty-input behavior to its configured writer.

## SOLID Considerations

### Single Responsibility Principle

`FileSink` has one primary responsibility: coordinating storage access and serialization to deliver batches to a file resource.

It does not implement filesystem operations or format-specific serialization.

### Open/Closed Principle

New writer implementations can be introduced without modifying `FileSink`. New storage implementations could also satisfy the protocol, but none beyond `LocalFileSystem` is currently included in the supported project scope.

For example, adding a new local-compatible writer does not require changes to the sink implementation.

No factory, registry, or plugin framework is required at this layer.

### Liskov Substitution Principle

Any implementation satisfying `FileSystem` can be supplied as storage, and any implementation satisfying `TabularWriter` can be supplied as a writer, provided it preserves the documented behavioral contracts, including writable-stream behavior, iterable consumption, and exception propagation.

### Interface Segregation Principle

`FileSink` depends on two small protocols:

* `FileSystem` provides writable resource access.
* `TabularWriter` provides format-specific serialization.

Neither protocol needs unrelated operations such as pipeline orchestration or data transformation.

### Dependency Inversion Principle

`FileSink` depends on protocols rather than concrete storage and writer classes.

This keeps sink orchestration independent of local filesystem details and particular file formats.

## Design Constraints

The implementation should remain small:

* Accept a destination path, `FileSystem`, and `TabularWriter`.
* Use `FileSystem.open_write()` to obtain the output stream.
* Pass the iterable of batches and stream to `TabularWriter.write()`.
* Open the destination once per write operation.
* Close the stream reliably.
* Propagate underlying exceptions.
* Avoid format detection, factories, registries, retries, and append-mode configuration until concrete requirements justify them.

The central design principle is:

**`FileSink` coordinates serialization and storage; the writer handles the format and iterable of batches, while the storage implementation handles the destination.**
