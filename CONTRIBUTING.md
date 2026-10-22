
# Contributing to ETLRelay

Thank you for your interest in contributing to ETLRelay.

ETLRelay is an open-source Python framework for building lightweight,
composable ETL pipelines. Development emphasizes test-driven development,
explicit component contracts, maintainability, and incremental changes.

Contributions are welcome, including bug fixes, tests, documentation
improvements, and focused feature proposals.

## Before contributing

Before starting work:

1. Review the [README](README.md), [documentation](https://apaquette.github.io/ETLRelay/),
   and [roadmap](docs/roadmap.md).
2. Search existing issues and pull requests for related work.
3. Open an issue before proposing significant features, new abstractions,
   or architectural changes.
4. Keep changes focused on a concrete requirement.

ETLRelay deliberately avoids introducing additional frameworks, storage
backends, or architectural layers without demonstrated use cases.

Not every proposed feature will be accepted.

## Development environment

ETLRelay supports CPython 3.12, 3.13, and 3.14. Python 3.12 is the
default development and static-analysis baseline.

The project uses:

- Nix flakes for the development environment.
- uv for dependency management and lockfiles.
- pytest and pytest-cov for testing.
- Ruff for linting and formatting.
- Pyright for static type checking.
- MkDocs for documentation.

Clone the repository:

```bash
git clone https://github.com/apaquette/ETLRelay.git
cd ETLRelay
```

Enter the Nix development environment:

```bash
nix develop
```

Synchronize the project dependencies:

```bash
uv sync --locked --all-groups
```

Nix is recommended but not required. Contributors using another
environment must provide a supported Python interpreter and the
required development tools.

See [Development](docs/development.md) for additional setup and
verification instructions.

## Development workflow

The `dev` branch is the integration branch for ongoing development.
The `main` branch is used for verified releases.

Create a feature or fix branch from `dev`:

```bash
git switch dev
git pull --ff-only
git switch -c feature/short-description
```

Make changes in small, reviewable increments.

When finished, open a pull request targeting `dev`.

Do not target `main` directly for ordinary features, bug fixes,
or documentation changes.

## Test-driven development

ETLRelay follows a red-green-refactor development cycle:

1. Define the expected behavior and acceptance criteria.
2. Add a failing test for the requirement or regression.
3. Implement the minimum change required to pass the test.
4. Refactor while preserving the verified behavior.
5. Run the relevant tests and quality checks.
6. Update documentation where behavior or public contracts change.

Prefer testing security and validation rules at the component boundary
responsible for enforcing them.

Use unit tests for isolated behavior, integration tests for component
interactions, and functional tests for complete pipelines.

Tests should use temporary resources and synthetic data rather than
external production services or real credentials.

## Quality checks

Run the following checks before submitting a pull request:

```bash
uv run pytest --cov=etlrelay --cov-branch \
    --cov-report=term-missing --cov-fail-under=90.1

uv run ruff check src tests
uv run ruff format --check src tests
uv run pyright
uv run mkdocs build --strict
```

CI also performs dependency checks, distribution verification, and
installed-package compatibility testing.

A pull request must pass the applicable required CI checks before
merging.

## Code and architecture guidelines

- Preserve existing public contracts unless an intentional change
  has been discussed and documented.
- Prefer composition, small protocols, and explicit dependencies.
- Avoid unnecessary inheritance, generic frameworks, and premature
  abstraction.
- Keep storage access, serialization, processing, and orchestration
  responsibilities separate.
- Preserve useful underlying exceptions and resource ownership
  contracts.
- Do not introduce dependencies without a concrete requirement.
- Follow the existing formatting, naming, and typing conventions.
- Update tests and documentation alongside behavioral changes.

Changes to YAML configuration must preserve the documented schema
contract or clearly explain any intentional compatibility change.

## Security considerations

Never commit credentials, tokens, private datasets, or sensitive
connection information.

Use synthetic values in tests, issues, documentation, and examples.

Do not report suspected vulnerabilities through public issues.
Follow the private reporting instructions in
[SECURITY.md](SECURITY.md).

Consider the security implications of changes involving filesystem
paths, SQL, configuration parsing, logging, and resource cleanup.

## Documentation

Update the relevant documentation when changing:

- Public interfaces or configuration properties.
- CLI commands and error behavior.
- Security or operational contracts.
- Supported platforms or Python versions.
- Installation and development procedures.

Documentation is maintained through MkDocs in the `docs/` directory.
Keep examples aligned with supported functionality.

Run `uv run mkdocs build --strict` to verify documentation changes.

## Pull requests

A pull request should include:

- A concise explanation of the problem and solution.
- References to related issues, where applicable.
- Tests covering the change or an explanation if tests are unnecessary.
- Documentation updates for observable changes.
- Any relevant compatibility, dependency, or security considerations.

Keep unrelated changes in separate pull requests.

Project maintainers may request revisions or decline changes that
do not fit the project's current scope.

## Community standards

All contributors are expected to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).

Constructive feedback, respectful discussion, and clear technical
communication are expected throughout the contribution process.

Thank you for helping improve ETLRelay.
