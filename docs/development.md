# Development

ETLRelay uses Nix flakes for its development environment, uv for Python dependencies and lockfiles, pytest for tests, Ruff for linting and formatting, Pyright for static typing, MkDocs for documentation, GitHub Actions for CI, and PyPI for distribution.

Python 3.12 is the default development interpreter. ETLRelay v0.8.0 supports CPython 3.12, 3.13, and 3.14.

## Development environment

Enter the Nix development shell:

```bash
nix develop
```

The shell provides Python 3.12, 3.13, and 3.14, along with the configured development tooling. Node.js is provided for Pyright.

The repository's `.python-version` selects Python 3.12 by default.

Synchronize the committed lockfile and all dependency groups:

```bash
uv sync --python 3.12 --locked --all-groups
```

Python 3.12 remains the baseline for development, Ruff, Pyright, and the full CI quality checks.

Other supported interpreter versions are used for compatibility testing without changing the project's primary development environment.

## Dependency integrity

Verify that the lockfile matches project metadata:

```bash
uv lock --check
```

Audit locked dependencies:

```bash
uv audit --locked --preview-features audit-command
```

Check the installed environment:

```bash
uv pip check --python .venv/bin/python
```

The vulnerability audit includes runtime and development dependency groups. An archived dependency may be reported as an adverse project status without being a known vulnerability.

A successful audit does not establish that dependencies are free from undiscovered vulnerabilities.

When changing dependencies, regenerate and review `uv.lock`. Prefer targeted dependency updates when resolving a specific security advisory.

## Quality checks

Run the full test suite with statement and branch coverage:

```bash
uv run pytest \
    --cov=etlrelay \
    --cov-branch \
    --cov-report=term-missing \
    --cov-report=xml \
    --cov-fail-under=90.1
```

The configured minimum coverage is 90.1%. The coverage threshold is enforced by CI.

Run linting, formatting, type checking, and documentation validation:

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run pyright
uv run mkdocs build --strict
```

For Python 3.12 compatibility, keep the configured Ruff and Pyright language targets aligned with the minimum supported Python version.

## Build and verify distributions

Remove previous build artifacts and build the source distribution and wheel:

```bash
rm -rf dist
uv build
```

Validate the distribution metadata:

```bash
uvx --from 'twine>=7,<8' twine check dist/*
```

Verify the packaged modules, metadata, runtime dependency declarations, and CLI entry point:

```bash
uv run python tests/packaging/check_distributions.py
```

The distribution verification checks the built archives, not just the repository source tree.

This does not replace installed-artifact testing: a valid archive can still contain runtime or dependency errors.

## Installed-wheel compatibility

The compatibility smoke test installs the built wheel into a clean virtual environment outside the repository checkout.

It verifies package imports, installed dependency consistency, CLI version/help output, YAML validation, and execution of a minimal CSV pipeline.

Run the checks with the additional supported interpreters:

```bash
uv run --no-project --python 3.13 \
    python tests/packaging/smoke_compatibility.py dist

uv run --no-project --python 3.14 \
    python tests/packaging/smoke_compatibility.py dist
```

Using `--no-project` prevents these compatibility checks from changing the repository's primary Python 3.12 environment.

The CI workflow additionally tests the installed wheel on macOS and Windows.

## CI coverage

The primary CI job runs on Ubuntu with Python 3.12 and checks:

- Lockfile consistency and dependency security.
- Installed dependency compatibility.
- Documentation, tests, coverage, linting, formatting, and types.
- Wheel and source-distribution builds.
- Distribution metadata and package contents.
- Installed CLI behavior and a complete local CSV pipeline.
- Selected CLI failure codes and sensitive-data disclosure regressions.

The compatibility matrix verifies the same built wheel in these additional configurations:

| Platform | Python | Verification |
|---|---|---|
| Ubuntu | 3.13 | Installed-wheel smoke |
| Ubuntu | 3.14 | Installed-wheel smoke |
| macOS | 3.12 | Installed-wheel smoke |
| Windows | 3.12 | Installed-wheel smoke |

The full test suite is not repeated for every matrix entry. These jobs verify the installed artifact and a representative execution path.

## Preview documentation

Start the local documentation server:

```bash
uv run mkdocs serve
```

MkDocs serves a preview and rebuilds pages as source files change.

Build the documentation with warnings treated as errors:

```bash
uv run mkdocs build --strict
```

Generated output is written to `site/` and should not be committed.

The API reference uses `mkdocstrings` to render Python docstrings. When public contracts change, update the relevant source docstrings, API reference, architecture documentation, and user-facing guides.

## Release verification

Before publishing a new version:

1. Confirm the intended version and supported Python range in `pyproject.toml`.
2. Regenerate and verify `uv.lock`.
3. Update the changelog, README, documentation homepage, and versioned documentation links.
4. Run dependency checks and the full quality suite.
5. Build fresh distribution artifacts and validate their contents.
6. Test the built wheel in clean environments outside the repository checkout.
7. Confirm the CI quality job and compatibility matrix pass.
8. Review the changeset for unintended API, dependency, or behavioral changes.
9. Follow the documented TestPyPI and production publication workflow.
10. Verify the published package, GitHub release, and versioned documentation.

See [Release Automation](development/release-automation.md) and the repository's `RELEASE_CHECKS.md` for the release procedure and acceptance records.

A successful editable installation is not evidence that the wheel or source distribution is correct.

## Development principles

ETLRelay follows incremental, test-driven development:

1. Establish the requirement and acceptance criteria.
2. Add focused tests.
3. Implement the minimum behavior needed.
4. Refactor without changing verified contracts.
5. Run quality and regression checks.
6. Update relevant documentation.

Prefer explicit component contracts and small abstractions. Avoid introducing new architectural layers without a demonstrated requirement.