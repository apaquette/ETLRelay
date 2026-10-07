# FlowForge

FlowForge is an open-source Python framework for building lightweight, composable ETL pipelines.

The project is designed around a simple pipeline model:

```text
Source → Processor(s) → Sink
```

Sources and sinks define the pipeline boundary. For file-based data, storage location and file format are deliberately separated:

```text
Storage Backend → File Reader → Processor(s) → File Writer → Storage Backend
```

This allows the same file-format implementation to work with different storage systems such as the local filesystem, S3, or HDFS without duplicating format-specific logic.

Pipelines will eventually be definable both programmatically and through YAML, with the same underlying execution model used in both cases.

## Project Status

**Phase 0 — Development Environment**

The project is currently in environment setup. No ETL functionality has been implemented yet.

The initial implementation will focus on:

* Composable pipeline components
* Batch-oriented data processing
* Apache Arrow as a common data representation
* Separation of storage backends from file formats
* Pluggable file readers and writers
* Integration with Polars for data transformation
* SQL and filesystem sources and sinks
* Declarative YAML job definitions
* Secure handling of configuration and secrets
* A small command-line interface
* Automated testing using TDD

The project will deliberately avoid unnecessary infrastructure and abstractions until they are justified by an actual requirement.

## Development Environment

The development environment is managed with Nix flakes.

Enter the development shell:

```bash
nix develop
```

The shell provides:

* Python 3.12
* uv
* Ruff
* Pyright
* Git

Nix provides system-level development tools and executables, while uv manages the Python project environment and Python dependencies.

The Python virtual environment is managed by uv at `.venv/`.

The project intentionally uses Nix-native versions of command-line development tools such as Ruff and Pyright. This avoids relying on prebuilt generic Linux executables that are incompatible with NixOS's standard runtime environment.

## Getting Started

After entering the development shell:

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

These commands should all execute successfully before beginning implementation work.

## Development Principles

### TDD

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
```

Tests are part of the design process rather than something added after implementation.

### Keep Architecture Small

Prefer simple, explicit abstractions over framework machinery.

An abstraction should exist because a concrete requirement justifies it, not because a future requirement might eventually need it.

The project should avoid speculative interfaces, excessive inheritance, and unnecessary configuration.

### Separate Storage from Serialization

Where file-based ETL is concerned, FlowForge separates:

* **Storage** — where data is located
* **Serialization** — how data is encoded
* **Processing** — how data is transformed

For example:

```text
S3
 │
 ▼
File Reader
 │
 ▼
CSV Format
 │
 ▼
Arrow Data
 │
 ▼
Processors
 │
 ▼
Arrow Data
 │
 ▼
CSV Format
 │
 ▼
File Writer
 │
 ▼
S3
```

This prevents the creation of separate implementations such as `S3CsvSource`, `LocalCsvSource`, and `HdfsCsvSource`.

A CSV implementation should not need to know where the file is stored.

### Independent Implementation

FlowForge is independently developed open-source software.

Implementation, APIs, documentation, tests, and design decisions should be developed from FlowForge's own requirements rather than copied from another codebase.

## Planned Architecture

The broader architecture is:

```text
                          Pipeline
                             │
                 ┌───────────┴───────────┐
                 │                       │
               Source                   Sink
                 │                       │
        ┌────────┴────────┐     ┌───────┴────────┐
        │                 │     │                │
    FileSource        SQLSource FileSink      SQLSink
        │                           │
        ├── StorageBackend          ├── StorageBackend
        │                           │
        └── FileReader              └── FileWriter
              │                           │
         Format Registry              Format Registry
              │                           │
       ┌──────┼──────┐             ┌──────┼──────┐
       CSV   JSON  Excel           CSV   JSON  Excel
       ...                       ...
```

File-based processing therefore follows:

```text
Storage Backend
      ↓
File Reader
      ↓
Format Strategy
      ↓
Arrow / batch representation
      ↓
Processor(s)
      ↓
Arrow / batch representation
      ↓
Format Strategy
      ↓
File Writer
      ↓
Storage Backend
```

### Storage Backends

Storage backends represent where file data resides.

Potential implementations include:

* Local filesystem
* Amazon S3
* Azure Blob Storage / ADLS
* Google Cloud Storage
* SFTP
* HDFS
* Other object or filesystem-compatible storage systems

Storage backends should handle storage-specific concerns such as:

* Resource location
* Authentication
* Opening resources
* Reading and writing bytes
* Storage-specific errors
* Retries where appropriate

A storage backend should not contain CSV, JSON, Excel, or other format-specific parsing logic.

Additional storage backends will be introduced only when concrete requirements justify them. The initial implementation will validate the abstraction using the local filesystem before introducing remote storage systems.

### File Readers and Writers

`FileReader` and `FileWriter` provide the serialization boundary between storage and the common FlowForge data representation.

Format support will be implemented independently, using a strategy/registry approach.

Potential formats include:

* CSV
* JSON
* Excel
* YAML
* Parquet
* Other formats as justified by requirements

The format should normally be inferred from the resource path when possible, while allowing explicit format configuration when inference is insufficient or ambiguous.

For example:

```yaml
source:
  type: file
  path: ./data/customers.csv
```

could infer CSV automatically.

Explicit configuration could override inference:

```yaml
source:
  type: file
  path: ./data/customers
  format: csv
```

## Common Data Representation

File formats should be converted into a common batch-oriented representation for processing.

Apache Arrow is the planned common representation.

Polars and other data-processing libraries may operate on that representation where appropriate.

The architecture should avoid requiring processors to understand whether their input originated from CSV, JSON, S3, HDFS, or another storage/format combination.

## Planned Components

### Sources

Potential source types include:

* File source
* SQL source
* Future API or other data sources

A file source combines a storage backend with a file reader.

### Processors

Potential processors include:

* Map/transformation
* Filter
* Validation
* Column selection

Processors operate on the common data representation rather than storage-specific or serialization-specific objects.

### Sinks

Potential sink types include:

* File sink
* SQL sink
* Future API or other data sinks

A file sink combines a storage backend with a file writer.

### Orchestrator

The orchestrator will eventually be responsible for:

* Loading pipeline definitions
* Resolving configured components
* Constructing pipelines
* Executing pipelines
* Handling failures
* Supporting cancellation
* Producing execution results
* Logging and observability

Scheduling and multi-job orchestration are intentionally deferred until the core pipeline model is established.

## Configuration

YAML is planned as a declarative configuration format.

A future configuration may look conceptually like:

```yaml
name: customer-import

source:
  type: file
  storage: local
  path: ./data/customers.csv

processors:
  - type: validate
  - type: transform

sink:
  type: file
  storage: s3
  path: s3://warehouse/customers.csv
```

The exact schema is subject to change during implementation.

Configuration should describe **what a pipeline should do** rather than exposing unnecessary implementation details.

Secrets should not be stored directly in pipeline definitions. Secret handling will be designed separately.

## Security

Security is a first-class design concern.

Planned protections include:

* SQL parameterization
* SQL identifier validation
* Path traversal prevention
* Configuration validation
* Secret management
* Sensitive-data redaction
* Safe handling of storage credentials
* Appropriate validation of external resources

Security mechanisms should be implemented at the layer where the relevant risk exists rather than centralized into an unrelated security abstraction.

## Testing

Testing follows the TDD development model.

### Unit Tests

Examples include:

* Pipeline composition
* Storage backend behavior
* File format readers and writers
* Format detection
* Data transformations
* Configuration validation
* Security validation

### Integration Tests

Examples include:

* Local filesystem operations
* SQL connections
* File format integration
* Storage backend integration

External services such as S3 should use appropriate test doubles or controlled integration environments rather than requiring external infrastructure for ordinary unit tests.

### End-to-End Tests

The project will eventually test complete flows such as:

```text
YAML
 ↓
Configuration
 ↓
Pipeline
 ↓
Storage
 ↓
Reader
 ↓
Processor(s)
 ↓
Writer
 ↓
Storage
```

## Planned Project Structure

```text
flowforge/
├── src/
│   └── flowforge/
├── tests/
├── examples/
├── docs/
├── .gitignore
├── flake.nix
├── flake.lock
├── pyproject.toml
├── README.md
├── LICENSE
└── NOTICE
```

Generated files and local development state such as `.venv/`, Nix development artifacts, Python caches, test output, and local ETL data are excluded through `.gitignore`.

The internal Python package structure will be established incrementally as concrete requirements emerge.

The project should avoid creating a large package hierarchy before the underlying responsibilities have been validated through implementation and tests.

## Development Workflow

Each implementation unit follows:

1. Define the requirement
2. Define acceptance criteria
3. Identify the smallest useful design
4. Write failing tests
5. Implement the minimum required behavior
6. Make the tests pass
7. Refactor where justified
8. Run the full test suite
9. Update documentation
10. Commit the completed change

The project should remain in a working state at the end of each phase.

## Current Phase

**Phase 0 — Development Environment**

Phase 0 is complete when:

* Nix development shell works
* Required Python version is available
* uv is available
* Git is available
* Ruff is available
* Pyright is available
* `uv sync` works
* Project installs locally
* pytest executes
* Ruff executes
* Pyright executes
* Initial documentation is present
* `.gitignore` is present
* License files are present

The next phase will define the functional requirements and acceptance criteria for the core pipeline model.

## License

FlowForge is licensed under the Apache License, Version 2.0.

See `LICENSE` for the full license text.
