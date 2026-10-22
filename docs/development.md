# Development

ETLRelay uses Nix flakes for its development environment, uv for Python
dependencies and lockfiles, pytest for tests, Ruff for linting and formatting,
Pyright for static typing, MkDocs for documentation, GitHub Actions for CI,
and PyPI for distribution.

Python 3.12 is the default development interpreter. ETLRelay supports
CPython 3.12, 3.13, and 3.14.

Contributors should review the
[Contribution Guidelines](https://github.com/apaquette/ETLRelay/blob/main/CONTRIBUTING.md)
before submitting changes. This page provides the detailed development and
verification commands referenced by those guidelines.

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

## Installed-artifact compatibility

The compatibility smoke test installs both the wheel and source distribution into separate clean virtual environments outside the repository checkout. Source installation uses an isolated build from the archive.

It verifies public imports, dependency consistency, direct CSV/Parquet/SQLite pipelines, CLI version/help output, YAML validation, and a minimal CSV CLI pipeline. Use `--artifact wheel` or `--artifact sdist` to select one artifact; the default is `both`.

Run the checks with the additional supported interpreters:

```bash
uv run --no-project --python 3.13 \
    python tests/packaging/smoke_compatibility.py dist

uv run --no-project --python 3.14 \
    python tests/packaging/smoke_compatibility.py dist
```

Using `--no-project` prevents these compatibility checks from changing the repository's primary Python 3.12 environment.

The CI workflow tests both artifacts on every declared Python/platform combination, including macOS and Windows. See the [packaging verification record](development/packaging-verification.md) for baseline CI evidence, local results, and checks pending CI.

## CI coverage

The primary CI job runs on Ubuntu with Python 3.12 and checks:

- Lockfile consistency and dependency security.
- Installed dependency compatibility.
- Documentation, tests, coverage, linting, formatting, and types.
- Wheel and source-distribution builds.
- Distribution metadata and package contents.
- Installed CLI behavior and a complete local CSV pipeline.
- Selected CLI failure codes and sensitive-data disclosure regressions.

The compatibility matrix verifies the same built wheel and source distribution in these additional configurations:

| Platform | Python | Verification |
|---|---|---|
| Ubuntu | 3.13 | Wheel and sdist smoke |
| Ubuntu | 3.14 | Wheel and sdist smoke |
| macOS | 3.12 | Wheel and sdist smoke |
| Windows | 3.12 | Wheel and sdist smoke |

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
6. Test both built artifacts in separate clean environments outside the repository checkout.
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

## Contributing

ETLRelay welcomes contributions that improve reliability, security,
documentation, testing, and supported functionality.

Development emphasizes test-driven development, explicit component contracts,
maintainability, and incremental improvements.

The repository provides the following community documentation:

- [Contribution Guidelines](https://github.com/apaquette/ETLRelay/blob/main/CONTRIBUTING.md)
  — development setup, coding practices, testing, and pull request requirements.
- [Code of Conduct](https://github.com/apaquette/ETLRelay/blob/main/CODE_OF_CONDUCT.md)
  — community participation expectations and private reporting procedures.
- [Accessibility Statement](https://github.com/apaquette/ETLRelay/blob/main/ACCESSIBILITY.md)
  — accessibility considerations, limitations, and feedback procedures.
- [Security Policy](https://github.com/apaquette/ETLRelay/blob/main/SECURITY.md)
  — supported security reporting procedures.

### Development Workflow

The `dev` branch is the integration branch for ongoing development.
The `main` branch contains verified releases.

Contributors should create feature or fix branches from `dev` and submit
pull requests targeting `dev`.

Significant features, new abstractions, or architectural changes should
be discussed through a GitHub issue before implementation.

The v1.0 feature set is stable. New capabilities are evaluated through
the post-v1.0 roadmap rather than being added automatically to maintenance
releases.

### Bug Reports and Feature Requests

The repository provides standardized GitHub issue templates for:

- **Bug reports** — reproducible failures, expected and observed behavior,
  environment information, and relevant diagnostics.
- **Feature requests** — use cases, proposed behavior, alternatives, and
  compatibility considerations.

[Create an issue](https://github.com/apaquette/ETLRelay/issues/new/choose).

For defects, include the affected ETLRelay version, Python version,
operating system, and a minimal reproduction using synthetic data.

Do not include credentials, connection URLs, private datasets, or
other sensitive information in public reports.

Suspected security vulnerabilities must be reported privately using the
procedures described in the
[Security Policy](https://github.com/apaquette/ETLRelay/blob/main/SECURITY.md).

### Pull Requests

Pull requests should:

1. Describe the problem and the implemented solution.
2. Include focused tests or explain why tests are unnecessary.
3. Preserve existing public contracts unless an intentional change
   has been discussed and documented.
4. Update documentation when behavior, configuration, or interfaces change.
5. Identify relevant compatibility, dependency, and security implications.
6. Pass the applicable tests and quality checks before merging.

GitHub provides a pull request template to guide contributors through
these requirements.

Keep unrelated changes in separate pull requests.

### Executable Documentation

Executable documentation is checked by
`tests/functional/test_cli_installed.py::test_installed_candidate_runs_documented_examples`.

This test runs the quick-start snippets and repository examples against an
installed wheel outside the source checkout.

When an intentional documentation example change alters behavior, update
the expected outputs and verify the installed-package execution path.

Do not substitute an editable installation for installed-artifact
verification.

### Accessibility

Contributors should consider accessibility when updating documentation,
CLI messages, examples, and community resources.

Prefer clear heading structures, descriptive links, text-based
instructions, and diagnostics that do not rely exclusively on colour
or visual presentation.

Accessibility issues can be reported through GitHub Issues.

See the
[Accessibility Statement](https://github.com/apaquette/ETLRelay/blob/main/ACCESSIBILITY.md)
for additional guidance.

## Extending through Python protocols

An application can pass its own `Source`, `Processor`, `Sink`, tabular reader,
writer, or filesystem implementation directly to the corresponding constructors.
No inheritance or registration is required for direct Python composition.
Respect the documented signatures, schema compatibility, and resource ownership.

`examples/custom_processor.py` implements `UppercaseNames.process(batch) -> Batch`
using Arrow, then supplies it to `Pipeline` alongside the built-in CSV source
and sink. It preserves field types/nullability and propagates invalid input
errors. Run it with the installed candidate:

```bash
python examples/custom_processor.py
```

The existing explicit registry/factory/validator types also support deliberate
application composition, as described in the
[registry reference](architecture/component-registry.md). Such registrations do
not modify the default CLI catalog. Automatic plugin discovery and YAML-driven
arbitrary imports remain unsupported. Keep custom components trusted, document
their failure/cleanup behavior, and test them independently.
