# ETLRelay

ETLRelay is an open-source Python framework for building lightweight, composable ETL pipelines.

It uses a simple pipeline model:

```text
Source → Processor(s) → Sink
```

A source produces batches of data, processors transform those batches, and a sink consumes the results.

For file-based pipelines, ETLRelay separates storage access from format parsing and serialization:

```text
FileSystem → Reader → Batch → Processor(s) → Writer → FileSystem
```

This separation allows file sources and sinks to compose storage and format implementations independently. CSV and Parquet readers/writers use the same file source/sink abstractions without format-specific branches in those components.

ETLRelay is being developed incrementally, with test-driven development, explicit component contracts, and a focus on keeping the architecture small.

## Installation

Install ETLRelay from PyPI:

```bash
pip install etlrelay
```

## Documentation

See the [ETLRelay documentation](https://apaquette.github.io/ETLRelay/0.6.0) for usage instructions, examples, and API details.


## Project Status

**Current release: `0.6.0` — declarative YAML configuration**

The release includes the batch model, pipeline, local filesystem access, CSV and Parquet readers/writers, file source and sink, path validation, SQL source/sink implementations, and a versioned YAML configuration path. YAML configuration is loaded and validated separately from runtime component construction; the shared component catalog and `PipelineBuilder` compose supported registrations into an executable pipeline.

Unit tests validate individual components. Integration and functional tests exercise their composition.

The current implementation establishes the foundation for further
development. ETLRelay is not yet a complete ETL product, and its public
API may evolve before `1.0.0`.

The v0.4.0 milestone stabilizes and documents the local storage contract,
including stream ownership, path containment, error propagation, output
creation, overwrite behavior, and resource cleanup. It does not introduce
a new storage backend.

### Implemented Components

| Component         | Responsibility                                                  |
| ----------------- | --------------------------------------------------------------- |
| `Batch`           | Represents tabular data using Apache Arrow                      |
| `Source`          | Defines the contract for producing batches                      |
| `Processor`       | Defines the contract for transforming a batch                   |
| `Sink`            | Defines the contract for consuming batches                      |
| `Pipeline`        | Coordinates source, processor, and sink execution               |
| `FileSystem`      | Defines the interface for opening binary streams                |
| `LocalFileSystem` | Provides local filesystem access                                |
| `PathValidator`   | Enforces local filesystem path containment                      |
| `Reader`          | Defines the contract for reading data from a binary stream      |
| `CsvReader`       | Parses CSV data into ETLRelay batches                          |
| `ParquetReader`   | Parses Parquet data into ETLRelay batches                      |
| `Writer`          | Defines the contract for serializing batches to a binary stream |
| `CsvWriter`       | Serializes ETLRelay batches as CSV                             |
| `ParquetWriter`   | Serializes ETLRelay batches as Parquet                         |
| `FileSource`      | Composes a filesystem and reader to produce batches             |
| `FileSink`        | Composes a filesystem and writer to consume batches             |
| `SqlSource`     | Reads SQL query results into batches using SQLAlchemy           |
| `SqlSink`       | Appends batch rows to an existing SQL table                     |
| `KeyValueReader` | Defines the mapping-shaped document reader contract              |
| `YamlReader`     | Safely parses one YAML configuration document                    |
| `ConfigLoader`   | Reads, parses, and validates configuration documents             |
| `ConfigValidator` | Validates schema version 1 and its component sections            |
| `ComponentCatalog` | Shares built-in registries, validators, factories, and SQL service |
| `PipelineBuilder` | Builds runtime pipelines from validated configuration mappings   |


### Planned Capabilities

The following are not part of the v0.6.0 release contract and remain possible future work:

- Additional document and tabular formats, including a JSON configuration reader.
- Additional built-in data transformation processors.
- A command-line interface (planned for the v0.7.0 milestone).
- Additional runtime integrations if concrete use cases justify their maintenance cost.

S3, HDFS, and other remote-storage backends are outside the v0.4.0
milestone and the planned v1.0.0 scope. Additional storage and platform
integrations may be reviewed after v1.0.0 if concrete requirements justify
them. No particular backend, implementation, or release date is promised.

Features will be added when requirements justify them. The project will
not introduce scheduling, distributed execution, or other orchestration
infrastructure merely to anticipate future needs.


## Architecture

### Pipeline Execution

The pipeline provides the central execution model:

```text
Source
  │
  ▼
Iterable[Batch]
  │
  ▼
Processor 1
  │
  ▼
Processor 2
  │
  ▼
    ...
  │
  ▼
Sink
```

The pipeline applies processors in their configured order to each batch. With no processors, batches pass through unchanged.

Execution is synchronous. Exceptions propagate to the caller rather than being silently discarded or handled by an elaborate recovery framework.

### Separation of Storage and Serialization

ETLRelay keeps resource access independent of file-format handling.

The `FileSystem` protocol defines operations for opening readable and writable binary streams. `LocalFileSystem` implements that protocol for local files and uses `PathValidator` to enforce its permitted filesystem boundary.

Readers and writers operate on streams rather than filesystem paths.

For example, CSV reading follows:

```text
LocalFileSystem.open_read(path)
          │
          ▼
      BinaryIO
          │
          ▼
       CsvReader
          │
          ▼
        Batch
```

CSV writing follows the reverse path:

```text
        Batch
          │
          ▼
       CsvWriter
          │
          ▼
      BinaryIO
          │
          ▼
LocalFileSystem.open_write(path)
```

`FileSource` composes a filesystem and a reader. `FileSink` composes a filesystem and a writer.

This prevents source and sink implementations from becoming coupled to individual storage technologies or serialization formats.

For file-based pipelines, the current implementation supports the local filesystem with CSV and Parquet. SQL input/output is a separate source/sink integration rather than a file-format or storage variant.

### SQL Sources and Sinks

`SqlSource` and `SqlSink` implement the core source/sink contracts using SQLAlchemy. They are separate from file storage and file-format readers/writers. Query values can be supplied as bound parameters; the sink appends to an existing table using one transaction per non-empty batch. The caller owns the SQLAlchemy engine. SQLite is the reference integration-test backend; see [SQL source and sink](docs/architecture/sql_source_and_sink.md) for identifier handling, empty-data behavior, transaction boundaries, and limitations.

### Declarative YAML Configuration

Schema version 1 defines a closed set of supported components: file and SQL sources/sinks, local storage, CSV/Parquet file formats, and the `select_columns`, `rename_columns`, and `filter_rows` processors. The schema requires `version`, `source`, `processors`, and `sink`; unsupported keys and types are rejected.

The configuration lifecycle is `ConfigLoader` → `ConfigValidator` → `PipelineBuilder` → `Pipeline.run()`. Loading and validation do not construct runtime components. The builder resolves all configured component registrations and preflights SQL connection environment-variable references before invoking component factories. It returns a pipeline but does not execute it.

For SQL configuration, YAML stores an environment-variable name such as `ETLRELAY_SOURCE_DATABASE_URL`, not the resolved connection URL. Missing/empty variables fail before component factories or source/sink I/O. The `PipelineBuilder` owns the lifecycle of engines created by the catalog's shared `SqlEngineFactory`; callers close the builder after execution. Direct Python `SqlSource`/`SqlSink` engine ownership remains unchanged.

See the [YAML Configuration reference](https://apaquette.github.io/ETLRelay/0.6.0/configuration/) for the versioned schema, examples, supported combinations, and validation errors.

### Common Data Representation

ETLRelay uses Apache Arrow tables as the underlying tabular representation within `Batch`.

Readers convert external data into batches. Processors operate on batches, and writers serialize batches for output.

This provides a common data boundary between file formats and pipeline components.

Polars is a potential transformation tool for future processors; its use is not required by the current core pipeline implementation.

### Component Contracts

ETLRelay uses Python protocols to define component boundaries where substitutability is useful.

The core contracts are deliberately small:

```text
Source
    Produces batches

Processor
    Transforms a batch

Sink
    Consumes batches
```

For file-based operations:

```text
FileSystem
    Opens binary streams

Reader
    Converts stream data into batches

Writer
    Serializes batches to a stream
```

Concrete implementations remain independent of higher-level orchestration. The configuration path uses explicit registries and factories where a YAML component name must resolve to a validator and runtime implementation. It does not use a general dynamic plugin system, import-by-string, or reflection-based construction.

## Development Environment

The development environment is managed with Nix flakes.

Enter the development shell:

```bash
nix develop
```

The environment provides:

* Python 3.12
* uv
* Ruff
* Pyright
* Git

Nix provides system-level development tools and executables, while uv manages the Python project environment and Python dependencies.

The Python virtual environment is managed by uv in `.venv/`.

The project uses Nix-provided versions of command-line development tools such as Ruff and Pyright to avoid relying on generic Linux executables that may be incompatible with NixOS.

## Getting Started

Enter the development shell:

```bash
nix develop
```

Install or synchronize Python dependencies:

```bash
uv sync
```

Run the test suite:

```bash
uv run pytest
```

Run the linter:

```bash
ruff check .
```

Check formatting:

```bash
ruff format --check .
```

Run static type checking:

```bash
pyright
```

Run these checks before committing implementation changes.

## Development Principles

### Test-Driven Development

Development follows a small, explicit cycle:

```text
Requirement
    ↓
Acceptance Criteria
    ↓
Failing Test
    ↓
Minimal Implementation
    ↓
Passing Test
    ↓
Refactor
    ↓
Validation
```

Tests establish expected behavior before implementation. Unit tests validate components independently, while integration and functional tests verify that components work together.

### Keep Architecture Small

Prefer simple, explicit abstractions over framework machinery.

An abstraction should exist because a concrete requirement justifies it, not because a hypothetical future requirement might eventually need it.

Prefer composition and small protocols over unnecessary inheritance. Add configuration, extension mechanisms, and additional layers only when they solve an identified problem.

### Separate Responsibilities

Each component should have one clearly defined responsibility:

* `PathValidator` checks local path containment.
* `LocalFileSystem` handles local filesystem access.
* Readers parse external representations.
* Writers serialize batches.
* Sources and sinks compose the relevant components.
* Processors transform batches.
* `Pipeline` coordinates execution.

Security checks should be implemented at the layer where the relevant risk exists.

### Independent Implementation

ETLRelay is independently developed open-source software.

Its implementation, interfaces, documentation, tests, and design decisions are developed from its own requirements and design process.

## Security

Security is a design concern from the beginning.

Current filesystem path validation resolves candidate paths and checks that they remain within the permitted base directory. It does not determine whether a path exists; filesystem operations handle existence and access errors.

Configuration uses a safe YAML loader, a strict versioned schema, and explicit component registrations. SQL connection URLs are referenced through environment-variable names rather than placed in YAML. The builder preflights required variables before constructing ETL components, and its SQL engine factory avoids exposing resolved connection URLs in its own errors. Environment variables are not a secrets vault; deployments remain responsible for controlling access to secrets and runtime diagnostics.

Further security work will be required as ETLRelay gains more capabilities. Areas for future development include:

* A command-line entry point for validate/run workflows (planned)
* JSON configuration reading, if a concrete use case justifies it
* Additional storage-specific authentication and access-control capabilities for future integrations

The current path-validation component is a filesystem containment control, not a complete filesystem sandbox or authorization system.

## Testing

Testing follows the TDD development model.

### Unit Tests

Unit tests validate components independently, including:

* Batch representation
* Pipeline execution and processor ordering
* Path containment
* Filesystem interactions
* CSV and Parquet parsing and serialization
* SQL source/sink validation, bound query values, table reflection, transactions, and resource cleanup
* File source and sink orchestration
* Error propagation and resource cleanup

### Integration Tests

Integration tests verify real local filesystem and CSV/Parquet operations plus SQLAlchemy/SQLite reads, writes, and round trips. Functional tests also cover mixed file/SQL pipelines.

### Functional Tests

Functional tests exercise complete workflows through the source, processing, and sink boundaries.

The suite should use temporary directories and controlled test inputs rather than relying on repository-local data or external infrastructure unnecessarily.

If additional storage backends or data sources are considered after v1.0.0,
their integration tests should be introduced alongside the corresponding
implementation. No such backend is included in the current release scope.

## Project Structure

The current package is organized around component responsibilities. The structure will evolve as additional features are implemented.

```text
src/
└── etlrelay/
    ├── core/
    │   ├── batch.py
    │   ├── source.py
    │   ├── processor.py
    │   ├── sink.py
    │   ├── reader.py
    │   └── writer.py
    ├── pipeline/
    │   └── pipeline.py
    ├── security/
    │   └── path.py
    ├── storage/
    │   ├── filesystem.py
    │   └── local.py
    ├── readers/
    │   ├── csv.py
    │   ├── parquet.py
    │   └── yaml.py
    ├── writers/
    │   ├── csv.py
    │   └── parquet.py
    ├── sources/
    │   ├── file.py
    │   └── sql.py
    ├── sinks/
    │   ├── file.py
    │   └── sql.py
    ├── config/
    │   ├── loader.py
    │   ├── validator.py
    │   ├── pipeline_builder.py
    │   ├── registry.py
    │   ├── sql_engine_factory.py
    │   ├── sources/
    │   ├── sinks/
    │   ├── storage/
    │   └── processors/
    ├── default_components.py
    └── file_formats.py

tests/
├── unit/
├── integration/
└── functional/

docs/
examples/
```

The tree is illustrative of the current component organization. It does not imply that every future feature or module has already been implemented.

Generated files and local development state—including `.venv/`, Python caches, test output, and local ETL data—should be excluded through `.gitignore`.

## Development Workflow

Each implementation unit follows these steps:

1. Define the requirement.
2. Establish acceptance criteria.
3. Choose the smallest suitable design.
4. Write failing tests.
5. Implement the minimum required behavior.
6. Confirm the tests pass.
7. Refactor where justified.
8. Run the full test suite and quality checks.
9. Update documentation.
10. Commit the completed change.

The project should remain in a working state throughout development.

## License

ETLRelay is licensed under the Apache License, Version 2.0.

See `LICENSE` for the full license text.
