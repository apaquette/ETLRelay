# FileSource Class Diagram

## Purpose

`FileSource` is a source component responsible for reading data from a configured file resource and producing ETLRelay `Batch` objects.

It composes two independent components:

* `FileSystem`, which provides access to the resource through a binary stream.
* `Reader`, which parses the resource and produces an iterable of `Batch` objects.

`FileSource` does not depend on a particular storage implementation or file format. This allows it to work with `LocalFileSystem` and future storage implementations, as well as `CsvReader` and future readers, without changing its implementation.

## Class Diagram

```mermaid
classDiagram
    class Source {
        <<protocol>>
        +read() Iterable~Batch~
    }

    class FileSource {
        -path: str
        -storage: FileSystem
        -reader: Reader
        +read() Iterable~Batch~
    }

    class FileSystem {
        <<protocol>>
        +open_read(path: str) BinaryIO
    }

    class Reader {
        <<protocol>>
        +read(stream: BinaryIO) Iterable~Batch~
    }

    class LocalFileSystem {
        +open_read(path: str) BinaryIO
    }

    class CsvReader {
        +read(stream: BinaryIO) Iterable~Batch~
    }

    class PathValidator {
        +validate(path: Path | str) Path
    }

    class Batch

    Source <|.. FileSource
    FileSystem <|.. LocalFileSystem
    Reader <|.. CsvReader

    FileSource --> FileSystem : uses
    FileSource --> Reader : uses

    LocalFileSystem --> PathValidator : validates paths with
    CsvReader --> Batch : produces
```

## Responsibilities

### FileSource

`FileSource` is responsible for:

* Storing the configured resource path.
* Opening the resource through the supplied `FileSystem`.
* Passing the resulting binary stream to the supplied `Reader`.
* Exposing the reader's batches through the `Source` interface.
* Ensuring the opened stream remains available while batches are being read.
* Closing the stream when iteration finishes, fails, or is explicitly closed.

`FileSource` is **not** responsible for:

* Implementing filesystem operations.
* Validating local filesystem path containment.
* Parsing CSV or other file formats.
* Constructing `Batch` objects directly.
* Transforming data.
* Writing files.
* Orchestrating pipeline execution.

### FileSystem

`FileSystem` defines the contract for accessing file resources.

Its implementations open resources for reading and provide binary streams. Storage-specific behavior, such as local path validation, remains within the concrete storage implementation.

`FileSource` depends on the protocol rather than on `LocalFileSystem`.

### Reader

`Reader` defines the contract for parsing a binary stream and producing an iterable of ETLRelay `Batch` objects.

Its implementations handle format-specific parsing. For example, `CsvReader` uses PyArrow to parse CSV data.

A reader may produce one or more batches. `FileSource` does not need to know how the reader divides its output into batches or how it interprets the underlying format.

## Dependency Relationship

```text
Source
  ▲
  │ implements
  │
FileSource
  ├── FileSystem
  │      └── LocalFileSystem
  │              └── PathValidator
  │
  └── Reader
         └── CsvReader
```

`FileSource` depends on the `FileSystem` and `Reader` protocols, not their concrete implementations.

This enables different combinations without modifying `FileSource`:

```text
LocalFileSystem + CsvReader
LocalFileSystem + ParquetReader
S3Storage       + CsvReader
HdfsStorage     + CsvReader
```

Additional combinations can be supported as new storage and reader implementations are introduced.

## Data Flow

The source coordinates the following operations:

```text
FileSource.read()
       │
       ▼
FileSystem.open_read(path)
       │
       ▼
  BinaryIO stream
       │
       ▼
Reader.read(stream)
       │
       ▼
Iterable[Batch]
       │
       ▼
Pipeline
```

The reader determines how many batches are produced. `FileSource` exposes those batches through the `Source` interface without performing additional format conversion or transformation.

The stream must remain open while the reader's iterable is consumed. This is particularly important when a reader produces batches lazily. The stream should be managed with a context manager so that it is closed reliably when iteration completes or terminates with an exception.

## Interface

```python
from collections.abc import Iterable

from etlrelay.core.batch import Batch
from etlrelay.core.reader import Reader
from etlrelay.storage.filesystem import FileSystem


class FileSource:
    def __init__(
        self,
        path: str,
        storage: FileSystem,
        reader: Reader,
    ) -> None:
        ...

    def read(self) -> Iterable[Batch]:
        ...
```

## Contract

| Operation                                        | Expected behavior                                                         |
| ------------------------------------------------ | ------------------------------------------------------------------------- |
| Construct with path, storage, and reader         | Stores the supplied dependencies and resource path                        |
| Read a valid resource                            | Produces an iterable of parsed batches                                    |
| Read a nonexistent local file                    | Propagates the storage error                                              |
| Read an invalid CSV resource                     | Propagates the reader's parsing error                                     |
| Read a resource outside the permitted local base | Propagates the path-validation error from local storage                   |
| Consume batches                                  | Keeps the opened stream available while the reader's iterable is consumed |
| Finish or terminate iteration                    | Closes the opened stream                                                  |
| Supply another storage implementation            | Works without modifying `FileSource`, provided it satisfies `FileSystem`  |
| Supply another reader implementation             | Works without modifying `FileSource`, provided it satisfies `Reader`      |

Exceptions are propagated rather than wrapped in a new `FileSource` exception hierarchy.

## SOLID Considerations

### Single Responsibility Principle

`FileSource` has one primary responsibility: coordinating storage access and format reading to produce batches for the pipeline.

It does not implement filesystem operations or format-specific parsing.

### Open/Closed Principle

New storage backends and reader implementations can be introduced without modifying `FileSource`.

For example, adding `ParquetReader` or `S3Storage` does not require changes to the source implementation.

No factory, registry, or plugin framework is required for this behavior.

### Liskov Substitution Principle

Any implementation satisfying `FileSystem` can replace another storage implementation, and any implementation satisfying `Reader` can replace another reader.

Substitutions must preserve their documented contracts, including binary-stream behavior, batch iteration, resource lifetime, and exception propagation.

### Interface Segregation Principle

`FileSource` depends on two small protocols:

* `FileSystem` provides resource access.
* `Reader` provides format parsing and batch production.

Neither protocol needs unrelated operations such as writing, transformation, or pipeline execution.

### Dependency Inversion Principle

`FileSource` depends on protocols rather than concrete storage and reader classes.

This keeps source orchestration independent of local filesystem details and specific file formats.

## Design Constraints

The initial implementation should remain small:

* Accept a resource path, `FileSystem`, and `Reader`.
* Use `FileSystem.open_read()` to obtain the stream.
* Pass the stream to `Reader.read()`.
* Expose the resulting batches through the `Source` interface.
* Keep the stream open for the duration of iteration.
* Close the stream reliably, including when iteration fails.
* Propagate underlying exceptions.
* Avoid format detection, factories, registries, retries, and additional chunking abstractions until concrete requirements justify them.

The central design principle is:

**`FileSource` coordinates resource access and batch production; the storage implementation handles the resource, and the reader handles the format.**
