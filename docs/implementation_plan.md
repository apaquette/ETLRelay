# FlowForge Implementation Plan

## Purpose

This document defines the incremental implementation plan for FlowForge.

FlowForge is intended to be a lightweight, composable Python framework for building ETL pipelines around:

```text
Source → Processor(s) → Sink
```

The implementation emphasizes:

* TDD
* Simple, explicit architecture
* Composability
* Separation of concerns
* Batch-oriented processing
* Apache Arrow as the common data representation
* Storage/serialization separation
* Secure handling of external resources
* Declarative YAML configuration
* Practical extensibility without speculative abstraction

Each phase follows the same SDLC:

```text
Requirements
    ↓
Acceptance Criteria
    ↓
Design
    ↓
Failing Tests
    ↓
Implementation
    ↓
Passing Tests
    ↓
Refactoring
    ↓
Documentation
    ↓
Verification
```

The project should remain functional at the end of every phase.

---

# Phase 0 — Development Environment

## Goal

Establish a reproducible Nix-based Python development environment and project skeleton.

## Tasks

* Create Nix flake
* Configure Python 3.12
* Configure uv
* Configure Git tooling
* Create `pyproject.toml`
* Configure pytest
* Configure ruff
* Configure pyright
* Establish `src/` package layout
* Establish `tests/`
* Create initial README
* Add Apache-2.0 `LICENSE`
* Add project `NOTICE`

## TDD

No production functionality is implemented in this phase.

The acceptance criteria are environment and tooling checks.

## Done When

```text
nix develop
uv sync
uv run pytest
uv run ruff check .
uv run pyright
```

all execute successfully.

---

# Phase 1 — Core Pipeline Model

## Goal

Define the smallest useful abstraction for:

```text
Source → Processor(s) → Sink
```

The core model should not know about:

* YAML
* S3
* HDFS
* CSV
* SQLAlchemy
* CLI concerns
* external configuration
* scheduling

## Requirements

The pipeline should be able to:

* accept a source;
* execute processors in order;
* pass processed data to a sink;
* represent successful execution;
* propagate failures predictably.

The initial data model should be batch-oriented rather than optimized around individual records.

## Design Questions

Determine through implementation:

* What constitutes a batch?
* What should a source yield?
* How are processors composed?
* What does a sink consume?
* How are failures represented?
* Is asynchronous execution required immediately?

Avoid solving streaming, distributed execution, scheduling, or parallelism at this stage.

## TDD

For each behavior:

1. Write acceptance criteria
2. Write failing tests
3. Implement minimum behavior
4. Refactor after tests pass

## Done When

A small in-memory pipeline can execute:

```text
Test Source
    ↓
Processor
    ↓
Test Sink
```

with comprehensive unit tests.

---

# Phase 2 — Common Data Representation

## Goal

Establish the representation passed between pipeline components.

Apache Arrow is the planned common representation.

## Requirements

Determine the minimum abstraction necessary to:

* represent tabular batches;
* pass batches between components;
* inspect schemas;
* support transformation;
* avoid coupling the pipeline engine to a specific storage format.

## Technology

* PyArrow
* Polars where useful for transformations

## TDD

Test:

* batch creation;
* schema handling;
* processor input/output;
* empty batches;
* multiple batches;
* invalid data where relevant.

## Done When

The core pipeline can operate on Arrow-compatible batches without knowing their original source format.

---

# Phase 3 — Storage Abstraction

## Goal

Separate **where data is stored** from **how it is encoded**.

The initial conceptual model is:

```text
FileSource
    │
    ├── Storage Backend
    │
    └── File Reader
```

and:

```text
FileSink
    │
    ├── Storage Backend
    │
    └── File Writer
```

## Initial Storage Backend

Implement:

```text
LocalFileSystem
```

first.

Do not implement S3 or HDFS until the storage abstraction has been validated against a real use case.

## Responsibilities

A storage backend may eventually handle:

* locating resources;
* opening resources;
* reading bytes;
* writing bytes;
* existence checks;
* storage-specific errors.

It should not contain CSV, JSON, Excel, or other format-specific logic.

## TDD

Test the storage contract independently of file formats.

Examples:

* open existing resource;
* missing resource;
* read bytes;
* write bytes;
* invalid path;
* path traversal prevention where applicable.

## Done When

A local filesystem backend can provide resources to a file reader and accept output from a file writer without knowing the underlying format.

---

# Phase 4 — File Reader and Writer

## Goal

Introduce serialization as a separate concern from storage.

The architecture becomes:

```text
Storage
   ↓
FileReader
   ↓
Format Strategy
   ↓
Arrow Batch
```

and:

```text
Arrow Batch
   ↓
Format Strategy
   ↓
FileWriter
   ↓
Storage
```

## Format Strategy

The reader/writer should support independently implemented formats.

Initial target:

```text
CSV
```

Additional formats should be added only when justified.

Potential future formats:

* JSON
* Excel
* YAML
* Parquet
* others

## Format Selection

The design should support:

1. Explicit format selection
2. Extension-based inference
3. Clear errors for unsupported or ambiguous formats

Example:

```yaml
format: csv
```

may explicitly select the format.

If no format is supplied, a `.csv` extension may be used for inference.

## TDD

Test:

* CSV reading;
* CSV writing;
* empty data;
* schemas;
* malformed input;
* unsupported formats;
* explicit format selection;
* extension-based detection.

## Done When

A local CSV file can be read into the common batch representation and written back without the reader/writer knowing whether the storage is local, S3, or another backend.

---

# Phase 5 — File Source and Sink

## Goal

Combine storage and serialization into usable pipeline components.

Conceptually:

```text
FileSource
    ├── StorageBackend
    └── FileReader
```

and:

```text
FileSink
    ├── StorageBackend
    └── FileWriter
```

## Requirements

A file source should:

* locate the resource through its storage backend;
* select the appropriate reader;
* produce Arrow-compatible batches.

A file sink should:

* accept Arrow-compatible batches;
* select the appropriate writer;
* write through its storage backend.

## TDD

Test combinations such as:

```text
Local filesystem
    +
CSV
```

while keeping the components independently testable.

## Done When

A complete pipeline can execute:

```text
Local CSV
    ↓
FileSource
    ↓
Processor(s)
    ↓
FileSink
    ↓
Local CSV
```

---

# Phase 6 — SQL Source and Sink

## Goal

Introduce database connectivity without coupling SQL functionality to the file architecture.

Conceptually:

```text
SQLSource
    ↓
SQLAlchemy
    ↓
Arrow Batches
```

and:

```text
Arrow Batches
    ↓
SQLAlchemy
    ↓
SQLSink
```

## Requirements

* Connection configuration
* Parameterized queries
* Safe identifier handling
* Batch reads
* Batch writes
* Transaction behavior
* Error handling

## Security

SQL injection prevention must be part of the design rather than a later hardening task.

## TDD

Use test databases or controlled integration environments for database integration tests.

Unit tests should not require a live external database.

## Done When

A complete database-to-file or file-to-database pipeline can execute using the established abstractions.

---

# Phase 7 — Additional Storage Backends

## Goal

Validate whether the storage abstraction generalizes beyond the local filesystem.

Possible implementations:

* S3
* HDFS
* Other object/file storage systems

Do not implement all of them automatically.

Each backend should be justified by an actual requirement.

## TDD

First test the storage contract independently.

Then add integration tests for the actual backend.

The format layer must remain unchanged.

For example:

```text
S3
 ↓
CSV Reader
 ↓
Processors
 ↓
CSV Writer
 ↓
Local filesystem
```

should be possible without creating an `S3CsvSource` or `LocalCsvSink`.

## Done When

At least one additional storage backend demonstrates that storage and serialization are genuinely independent.

---

# Phase 8 — Configuration Model

## Goal

Define a validated Python representation of declarative pipeline configuration.

YAML is an external representation, not the internal execution model.

Conceptually:

```text
YAML
 ↓
Configuration
 ↓
Pipeline
```

## Requirements

Configuration should describe:

* pipeline name;
* source;
* processors;
* sink;
* storage configuration;
* format configuration.

It should not expose unnecessary implementation details.

## TDD

Test:

* valid configuration;
* missing required fields;
* invalid component types;
* invalid formats;
* invalid storage configuration;
* useful validation errors.

## Done When

Valid configuration can be converted into a pipeline definition without directly executing the pipeline.

---

# Phase 9 — Component Registration and Resolution

## Goal

Provide a lightweight mechanism for resolving configured components.

Examples:

```yaml
source:
  type: file
```

```yaml
storage: local
```

```yaml
format: csv
```

The resolver maps configuration to implementations.

## Design Constraint

Do not create a general-purpose dependency injection framework.

Use simple registries/factories where appropriate.

Only introduce more sophisticated mechanisms if concrete requirements justify them.

## TDD

Test:

* known component resolution;
* unknown component errors;
* invalid configuration;
* dependency construction;
* format selection.

## Done When

A YAML configuration can resolve into the same pipeline model used by the programmatic API.

---

# Phase 10 — YAML Execution

## Goal

Connect declarative configuration to the execution engine.

The intended flow becomes:

```text
YAML
 ↓
Validation
 ↓
Configuration
 ↓
Component Resolution
 ↓
Pipeline
 ↓
Execution
```

## TDD

Add end-to-end tests covering complete pipelines.

Initial example:

```text
Local CSV
 ↓
Validation
 ↓
Transformation
 ↓
Local CSV
```

## Done When

A user can execute a complete ETL job from a YAML definition.

---

# Phase 11 — CLI

## Goal

Provide a small command-line interface for executing and inspecting pipelines.

Potential commands:

```bash
flowforge run pipeline.yaml
```

Additional commands should only be added when useful.

## Requirements

* Clear errors
* Appropriate exit codes
* Logging
* Configuration path handling
* Basic execution reporting

## Technology

Typer.

## Done When

A complete pipeline can be executed from the command line without requiring Python code.

---

# Phase 12 — Security and Hardening

## Goal

Perform systematic security review of the implemented system.

Areas include:

### Filesystem

* Path traversal
* Unsafe paths
* Unexpected file types
* Resource exhaustion

### SQL

* Injection
* Identifier validation
* Parameterization
* Transaction handling

### Configuration

* Unsafe YAML behavior
* Secret exposure
* Invalid configuration
* Sensitive values in logs

### Storage

* Credential handling
* Access configuration
* Error information leakage

## TDD

Security requirements should become regression tests.

## Done When

Identified security requirements have explicit automated coverage.

---

# Phase 13 — Observability and Operational Behavior

## Goal

Make pipeline execution understandable without building a large monitoring system.

Potential capabilities:

* Structured execution logging
* Pipeline start/end
* Component execution
* Batch counts
* Processing duration
* Errors
* Final execution status

Avoid introducing distributed tracing, metrics infrastructure, or external observability platforms unless a concrete requirement emerges.

## Done When

A user can understand what happened during a pipeline execution from its output/logs.

---

# Phase 14 — Documentation and Release

## Goal

Prepare FlowForge for external users.

## Documentation

Document:

* Installation
* Quick start
* Core concepts
* Pipeline composition
* Storage backends
* File formats
* Processors
* YAML configuration
* CLI
* Security considerations
* Development
* Testing
* Contributing

## Packaging

Verify:

* Python package builds correctly;
* package metadata is correct;
* dependencies are declared correctly;
* installation from a built package works;
* PyPI publishing workflow is reproducible.

## Release

Establish:

* versioning strategy;
* changelog;
* release workflow;
* GitHub Actions CI;
* package publishing.

## Done When

A new developer can clone the project, install it, understand the architecture, run the tests, and execute a basic ETL pipeline without needing project-specific assistance.

---

# Architectural Guardrails

These principles apply throughout every phase.

## 1. Storage Is Not Format

Do not create combinations such as:

```text
S3CsvSource
LocalCsvSource
HdfsCsvSource
```

Prefer:

```text
FileSource
    +
StorageBackend
    +
FileReader
```

This prevents combinatorial growth.

## 2. Format Is Not Processing

CSV, JSON, Excel, and other formats are serialization mechanisms.

Processors operate on the common batch representation.

## 3. Sources and Sinks Are Pipeline Boundaries

A source produces data for the pipeline.

A sink consumes data from the pipeline.

They should not contain unrelated format or storage responsibilities.

## 4. Abstractions Must Earn Their Existence

Do not implement an abstraction merely because it might be useful later.

Introduce it when:

* multiple implementations require it;
* a concrete requirement demands it;
* it substantially improves testability;
* or it provides a clearly defined architectural boundary.

## 5. Prefer Composition Over Inheritance

Prefer:

```text
FileSource(
    storage=...,
    reader=...
)
```

over deep inheritance trees.

## 6. Keep the Core Independent

The pipeline model should not depend on:

* S3
* HDFS
* SQLAlchemy
* YAML
* CLI frameworks
* specific file formats

Dependencies should point outward from the core.

## 7. TDD Drives the Design

Every significant behavior should begin with:

```text
Requirement
 ↓
Acceptance Criteria
 ↓
Failing Test
```

Architecture should emerge from tested requirements rather than being fully designed in advance.

## 8. Keep the Project Small

FlowForge is not intended to become an Airflow replacement, distributed compute engine, workflow scheduler, or enterprise integration platform during the initial development.

Build a useful ETL library first.

Expand only when real requirements justify expansion.

---

# Initial Milestone

The first meaningful milestone should be:

```text
Local CSV
    ↓
FileSource
    ↓
Processor
    ↓
FileSink
    ↓
Local CSV
```

implemented with:

```text
Storage Backend
File Reader
CSV Format
Arrow Batch
Processor
File Writer
```

This deliberately small vertical slice will validate the most important architectural assumption:

> **Storage, serialization, processing, and orchestration can remain independent components.**

Once that assumption is demonstrated through tests and a working pipeline, additional storage backends, formats, configuration, and orchestration can be added incrementally.
