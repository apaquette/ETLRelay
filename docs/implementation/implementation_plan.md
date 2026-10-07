# FlowForge Implementation Plan

## Purpose

This plan defines the implementation path for FlowForge using a test-driven, incremental approach.

The central rule is:

> Build the smallest useful end-to-end behavior first. Introduce abstractions only when concrete requirements and tests justify them.

The project should not begin by creating a large set of abstract interfaces. A concrete implementation must exist early enough that the abstractions can be evaluated against real behavior.

The target pipeline remains:

```text
Source → Processor(s) → Sink
```

For file-based ETL, the intended separation remains:

```text
Storage → Serialization → Processing → Serialization → Storage
```

However, these boundaries will be introduced incrementally rather than all at once.

---

## Development Principles

### TDD

Every implementation unit follows:

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
Integration / Functional Test
    ↓
Documentation
    ↓
Commit
```

Do not implement an abstraction before a test demonstrates the behavior it needs to support.

### SOLID Without Over-Engineering

SOLID principles should guide the design, but they should not become a reason to create unnecessary classes or interfaces.

In particular:

- **Single Responsibility:** separate responsibilities when they have distinct reasons to change.
- **Open/Closed:** use composition where adding a new implementation should not require changing unrelated code.
- **Liskov Substitution:** concrete implementations must honor the behavioral contract of the abstraction they implement.
- **Interface Segregation:** prefer small contracts over large interfaces.
- **Dependency Inversion:** higher-level pipeline behavior should depend on small stable contracts where this is demonstrably useful.

The project should prefer:

- composition over inheritance;
- Python protocols or small interfaces over deep class hierarchies;
- concrete behavior before speculative extensibility;
- one abstraction at a time.

### Vertical Slices Before Generalization

A feature is not considered validated merely because an abstract pipeline can be constructed.

Each major architectural boundary should eventually be demonstrated by a concrete path through the system.

The first meaningful slice is:

```text
Local CSV File
     ↓
Concrete File Source
     ↓
Processor
     ↓
Concrete File Sink
     ↓
Local CSV File
```

This should work before remote storage, SQL, YAML, orchestration infrastructure, or a large plugin system are introduced.

---

# Phase 0 — Development Environment

## Goal

Create a reproducible NixOS development environment and repository baseline.

## Scope

- Nix flake
- Python 3.12
- uv
- Ruff
- Pyright
- pytest
- pytest-cov
- Git
- `.gitignore`
- project metadata
- Apache-2.0 license and project notice

Nix provides the native command-line development tools. uv manages the Python project environment and Python dependencies.

## Do Not Implement

- ETL behavior
- pipeline classes
- storage abstractions
- readers/writers
- YAML configuration
- SQL
- CLI

## Acceptance Criteria

```text
nix develop
     ↓
python
uv
ruff
pyright
git
```

all work correctly on NixOS.

The repository also has:

- a working `pyproject.toml`;
- a `.gitignore`;
- license files;
- a passing `uv sync`;
- an executable pytest invocation.

## Verification

```bash
nix flake check
nix develop

python --version
uv --version
ruff --version
pyright --version
git --version

uv sync
uv run pytest
ruff check .
ruff format --check .
pyright
```

---

# Phase 1 — Minimal Local CSV Pipeline

## Goal

Prove the core pipeline model using real input and output rather than abstract test doubles alone.

The first production-capable path should be:

```text
Local CSV
   ↓
File Source
   ↓
Processor(s)
   ↓
File Sink
   ↓
Local CSV
```

The implementation should use the smallest set of models necessary to make this work.

## Scope

Implement only:

- a batch representation;
- a small `Source` contract;
- a small `Processor` contract;
- a small `Sink` contract;
- a pipeline execution model;
- local filesystem access;
- CSV reading;
- CSV writing;
- one simple processor used to prove transformation;
- unit tests;
- integration tests;
- one functional end-to-end test.

Apache Arrow may be used as the batch representation because it is already the planned common representation for FlowForge.

## Important Design Constraint

Do not begin Phase 1 with separate abstract hierarchies for:

- every possible source;
- every possible sink;
- every storage backend;
- every format;
- every processor type.

Implement the local path first.

A useful initial composition can be as small as:

```text
Pipeline
 ├── Source
 │    └── FileSource
 │         └── LocalFileSystem + CsvReader
 │
 ├── Processor(s)
 │
 └── Sink
      └── FileSink
           └── LocalFileSystem + CsvWriter
```

The exact interfaces should be extracted from the tests rather than prescribed in advance.

## Batch Contract

The initial batch should represent a collection of tabular data, not an individual record.

The implementation should answer these questions through tests:

- What type represents a batch?
- Does a source yield one batch or multiple batches?
- Can an empty batch be processed?
- Can processors replace a batch?
- Does the sink consume one batch at a time?
- Does the pipeline support multiple batches from one source?

Do not optimize for streaming, record-at-a-time processing, or parallelism.

## TDD Sequence

Implement Phase 1 in the following order.

### 1. Define the smallest useful batch

#### Acceptance Criteria

A batch can:

- contain tabular data;
- be passed to a processor;
- be passed to a sink;
- represent an empty result.

#### Tests

Write unit tests that establish the expected batch behavior.

Do not add convenience methods until a test requires them.

#### Done

The batch contract is clear enough to use in a source, processor, and sink.

---

### 2. Define and test the pipeline execution contract

#### Acceptance Criteria

Given:

```text
Source
Processor A
Processor B
Sink
```

the pipeline:

1. obtains a batch from the source;
2. passes it to Processor A;
3. passes the result to Processor B;
4. passes the final result to the sink.

With zero processors, the source output goes directly to the sink.

Exceptions raised by the source, a processor, or the sink propagate to the caller unless an explicit failure-handling requirement has been introduced.

A successful run completes without requiring a special execution framework or result object.

#### Tests

Start with unit tests using test doubles:

- one batch passes from source to sink;
- processors execute in order;
- zero processors works;
- multiple batches work;
- processor output becomes the next processor's input;
- source failure propagates;
- processor failure propagates;
- sink failure propagates.

#### Minimal Implementation

Create only the pipeline behavior required by those tests.

Do not add:

- retries;
- recovery policies;
- cancellation;
- logging frameworks;
- execution IDs;
- asynchronous execution;
- scheduling.

---

### 3. Implement the concrete local filesystem source path

#### Acceptance Criteria

A file source can read a local CSV file and produce the batch representation used by the pipeline.

At minimum:

- a valid file can be opened;
- CSV data is parsed;
- columns are preserved;
- values are represented consistently;
- missing files fail predictably.

#### Unit Tests

Test the CSV reader separately from filesystem behavior where practical.

Examples:

- valid CSV;
- header handling;
- multiple rows;
- empty data;
- malformed CSV;
- unsupported input conditions that the reader is responsible for.

#### Integration Tests

Use a temporary filesystem location and a real CSV file.

Verify:

```text
temporary CSV
    ↓
real LocalFileSystem
    ↓
real CsvReader
    ↓
batch
```

The integration test should not depend on the user's home directory or repository-local data.

---

### 4. Implement the concrete local filesystem sink path

#### Acceptance Criteria

A file sink can accept a batch and write a valid CSV file to a local path.

At minimum:

- output is created;
- output contains the expected columns;
- output contains the expected rows;
- parent-directory behavior is explicitly defined;
- invalid/unwritable paths fail predictably.

#### Unit Tests

Test CSV serialization independently where practical.

Examples:

- simple table;
- empty table;
- column names;
- values;
- repeated writes only if the behavior is required.

#### Integration Tests

Use a temporary filesystem location and a real output file.

Verify:

```text
batch
   ↓
real CsvWriter
   ↓
real LocalFileSystem
   ↓
CSV file
```

Read the resulting file back and verify its contents.

---

### 5. Connect the real source and sink through the pipeline

#### Acceptance Criteria

A complete local pipeline can execute:

```text
input.csv
   ↓
FileSource
   ↓
Processor
   ↓
FileSink
   ↓
output.csv
```

The processor must demonstrably change the data.

The test should prove that:

- the source reads actual data;
- the processor receives that data;
- the processor changes it;
- the sink writes the changed data;
- the output file contains the expected result.

#### Functional Test

Create one small, deterministic end-to-end scenario.

Example:

```text
Input:
name,age
Alice,30
Bob,40

Processor:
increase age by 1

Output:
name,age
Alice,31
Bob,41
```

The exact transformation is not architecturally important. Its purpose is to prove that data crosses the complete pipeline correctly.

Keep the fixture intentionally small and readable.

---

## Phase 1 Test Layers

### Unit Tests

Unit tests should isolate individual responsibilities.

Test:

- batch behavior;
- pipeline sequencing;
- processor ordering;
- source failure propagation;
- processor failure propagation;
- sink failure propagation;
- CSV parsing;
- CSV serialization.

Use simple test doubles where isolation provides value.

### Integration Tests

Integration tests should verify that concrete components work together with real resources.

At minimum:

```text
LocalFileSystem + CsvReader
LocalFileSystem + CsvWriter
FileSource + Processor + FileSink
```

Use pytest temporary directories/files.

Do not require:

- network access;
- S3 credentials;
- databases;
- external services.

### Functional Test

The functional test represents the user's observable workflow:

```text
CSV input → pipeline execution → CSV output
```

It should exercise the actual production classes used by a normal local pipeline.

This test is the most important Phase 1 proof that the architecture is useful.

---

## Phase 1 Failure Model

Keep the initial failure model deliberately simple.

The default rule is:

> Failures propagate to the caller.

Do not create a custom hierarchy of exception types unless a concrete requirement makes one necessary.

Errors should retain enough context to identify the failing operation, but adding a framework-wide error wrapper is deferred until real failure cases demonstrate a need.

---

## Phase 1 API Boundary

By the end of Phase 1, the design should have demonstrated the smallest useful contracts for:

```text
Source
    ↓
batch

Processor
    ↓
batch → batch

Sink
    ↓
batch
```

and:

```text
Pipeline
    ↓
Source → Processor(s) → Sink
```

The contracts should be based on the working local implementation.

If the tests show that a proposed abstraction is unnecessary, remove it rather than preserving it for theoretical extensibility.

---

## Phase 1 SOLID Check

Before completing the phase, review the implementation against:

### SRP

Can each component be described by one primary responsibility?

For example:

- pipeline coordinates execution;
- file source obtains and decodes input;
- CSV reader handles CSV parsing;
- processor transforms a batch;
- file sink encodes and stores output.

### OCP

Can another reader/writer be introduced without changing pipeline execution?

Do not implement that second format yet merely to prove it.

### LSP

Do the concrete source and sink behave according to their contracts?

Their behavior should be validated by the integration and functional tests.

### ISP

Are the contracts small?

Avoid interfaces containing operations that Phase 1 does not use.

### DIP

Does pipeline execution depend on the source/processor/sink contracts rather than directly constructing concrete filesystem or CSV classes?

Concrete objects should be composed at the application boundary.

---

## Phase 1 Completion Checklist

Phase 1 is complete when all of the following are true:

- [ ] Batch semantics are defined by tests.
- [ ] A source can provide a batch.
- [ ] Processors execute in deterministic order.
- [ ] Zero processors works.
- [ ] Multiple batches work, if the source supports them.
- [ ] A sink receives the final batch.
- [ ] Source failures propagate.
- [ ] Processor failures propagate.
- [ ] Sink failures propagate.
- [ ] A real local CSV source works.
- [ ] A real local CSV sink works.
- [ ] Unit tests pass.
- [ ] Integration tests pass.
- [ ] One functional end-to-end test passes.
- [ ] `ruff check .` passes.
- [ ] `ruff format --check .` passes.
- [ ] `pyright` passes.
- [ ] Documentation reflects the implemented behavior.
- [ ] The implementation contains no unused speculative abstractions.

## Phase 1 Suggested Repository Shape

Do not create the final package hierarchy yet.

A reasonable starting point is:

```text
src/
└── flowforge/
    ├── __init__.py
    ├── pipeline.py
    ├── batch.py
    └── fileio.py

tests/
├── unit/
│   ├── test_pipeline.py
│   ├── test_batch.py
│   └── test_fileio.py
├── integration/
│   └── test_local_csv.py
└── functional/
    └── test_csv_pipeline.py
```

This structure is intentionally provisional. Split modules further only when their responsibilities or size justify it.

---

# Phase 2 — Stabilize the Data Contract

## Goal

Turn the batch behavior discovered in Phase 1 into a deliberate, documented common data representation.

Apache Arrow becomes the primary FlowForge batch representation if Phase 1 confirms it fits the requirements.

## Focus

- Arrow table/record-batch semantics;
- schemas;
- empty batches;
- multiple batches;
- type consistency;
- conversion boundaries.

## TDD

Use the Phase 1 functional pipeline as a regression test while refining the data model.

Do not introduce Polars unless a concrete transformation requirement justifies it.

---

# Phase 3 — Extract and Validate Storage/Serialization Boundaries

## Goal

Generalize the local file implementation only after its responsibilities are understood.

The target separation becomes:

```text
FileSource
 ├── StorageBackend
 └── FileReader

FileSink
 ├── StorageBackend
 └── FileWriter
```

The first concrete backend remains the local filesystem.

## TDD

Refactor the existing local implementation under tests.

The existing functional test must continue to pass.

Only after the refactoring is stable should a second storage implementation be considered.

## Validation

A second backend should be added only when justified by an actual requirement. Its purpose is also to validate that the storage abstraction is genuinely useful.

Potential later backends include:

- S3;
- Azure Blob Storage / ADLS;
- Google Cloud Storage;
- SFTP;
- HDFS.

---

# Phase 4 — Additional File Formats

Introduce additional serialization formats only when requirements justify them.

Potential formats:

- JSON;
- Parquet;
- Excel;
- YAML.

Format inference and explicit format selection can be added here.

The existing CSV path remains a regression baseline.

---

# Phase 5 — Data Transformation Layer

Introduce useful production processors.

Potential processors:

- filter;
- column selection;
- mapping/transformation;
- validation.

Use Polars where it provides clear value, while keeping the processor contract independent of the storage and serialization layers.

---

# Phase 6 — SQL Sources and Sinks

Add SQL support using SQLAlchemy.

The SQL layer should be independently tested and should consume/produce the same common batch representation as file pipelines.

Security requirements such as parameterization and identifier validation are introduced with the SQL implementation rather than deferred indefinitely.

---

# Phase 7 — Configuration Model

Define a typed internal configuration model.

The model should describe pipeline intent without exposing unnecessary implementation details.

TDD should cover:

- required fields;
- defaults;
- invalid configuration;
- component references;
- path validation;
- secret references.

YAML parsing is still separate from pipeline execution at this stage.

---

# Phase 8 — Component Resolution and YAML Execution

Introduce:

- component registration;
- component resolution;
- YAML parsing;
- construction of pipelines from configuration.

The local CSV functional test should gain a configuration-driven counterpart:

```text
YAML
 ↓
Configuration Model
 ↓
Resolved Components
 ↓
Pipeline
 ↓
Local CSV Output
```

Avoid a plugin framework unless actual extensibility requirements justify one.

---

# Phase 9 — CLI

Add the Typer command-line interface around the existing application behavior.

The CLI should be a thin entry point rather than becoming part of the core pipeline model.

---

# Phase 10 — Security and Hardening

Strengthen security based on implemented capabilities.

Areas include:

- path traversal;
- safe file handling;
- SQL parameterization;
- SQL identifier validation;
- configuration validation;
- secrets;
- sensitive-data redaction;
- storage credentials;
- external resource validation.

Security checks belong in the layer where the associated risk occurs.

---

# Phase 11 — Observability and Operational Behavior

Add only the operational features required for real usage.

Potential areas:

- structured logging;
- execution summaries;
- useful error context;
- cancellation;
- metrics where justified.

Retries and recovery policies should be introduced only when a concrete failure mode requires them.

---

# Phase 12 — Documentation and Release

Prepare FlowForge for external use.

Potential work:

- API documentation;
- architecture documentation;
- examples;
- user guides;
- test documentation;
- CI;
- packaging;
- PyPI release;
- versioning;
- changelog.

The release process should document supported Python versions and supported integrations.

---

# Explicitly Deferred

The following are not part of the initial architecture unless later requirements justify them:

- streaming execution;
- distributed execution;
- parallel pipeline execution;
- scheduling;
- multi-job orchestration;
- workflow DAGs;
- retries as a general framework feature;
- plugin infrastructure;
- remote storage before the local model is validated;
- large-scale package hierarchies;
- framework-specific abstractions with no demonstrated use.

---

# Milestone Progression

The implementation should progress through these concrete proofs:

```text
Phase 1
Local CSV
   ↓
Source
   ↓
Processor
   ↓
Sink
   ↓
Local CSV
```

```text
Phase 2
Stable Arrow batch contract
```

```text
Phase 3
Local storage and serialization boundaries
```

```text
Phase 4
More file formats
```

```text
Phase 5
Useful processors
```

```text
Phase 6
SQL integration
```

```text
Phase 7–8
Configuration and YAML
```

```text
Phase 9+
CLI, security hardening, observability, release
```

Each phase must leave the project in a working state.

The architecture should emerge from these working slices rather than being designed completely in advance.
