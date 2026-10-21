# v0.9.0 Packaging and Compatibility Verification

Ticket: **0.9.0-06 — Verify package installation and supported environments**.
Reviewed baseline: `dev` commit `3d266d4d7fbe9f3fc595f96b67a3fbddb2fc7889`.

## Audit and changes

The baseline builds both distributions and checks metadata, modules, and CLI
entry points. Its compatibility jobs install only the wheel. The dependency
check compares names but can miss changed version bounds or extra dependencies;
it does not compare sdist dependency metadata.

This change reuses those scripts and adds:

- Separate wheel and source-distribution installations outside the checkout.
  Source installation builds from the archive using build isolation.
- Complete dependency-requirement comparison for both archive metadata sets,
  including bounds, extras, and environment markers; regression tests reject
  missing dependencies, changed/missing bounds, and extra dependencies.
- Required Apache licence and notice files in both archive types.
- Public component imports and direct CSV-to-Parquet-to-SQLite pipelines,
  including SQL source readback with data/schema assertions.
- The existing installed CLI version/help, YAML validation, and CSV execution
  checks for each artifact.
- Both-artifact smoke checks in the quality job, all compatibility jobs, and
  the existing TestPyPI/PyPI verification workflows.

There is no new support-matrix combination or runtime feature. Existing CI job
names are retained; the compatibility steps now test both archive types.

## Runtime dependencies and metadata

Runtime imports require PyArrow, PyYAML, SQLAlchemy, and Typer. Their existing
version constraints remain unchanged. Standard-library SQLite supplies the
reference database driver; other drivers are not bundled or claimed as tested.

Polars had no imports in the runtime implementation and no frozen-feature use
case. It is removed from runtime metadata and the lockfile. `packaging` is an
explicit CI-tool dependency for standards-aware requirement comparison, not a
new runtime dependency. Remaining locked package versions are unchanged.

At the packaging-review baseline, metadata declared `0.8.0` and CPython
`>=3.12,<3.15`; those verification archives did not replace the published files.
Beta preparation sets version `0.9.0` without changing the supported Python range.
See the [final readiness record](beta-readiness.md) for release-build results and
integrated CI requirements.

The archive checker verifies the 64 source Python modules, distribution name,
version, Python requirement, runtime requirements, licence/notice inclusion,
and the `etlrelay = etlrelay.cli:main` wheel entry point. Installation from the
sdist independently exercises its build metadata and generated entry point.

Checks validate selected resolved dependency versions within the declared
ranges; they do not test every possible dependency-version combination.

## Existing CI evidence

The baseline commit's
[successful CI run](https://github.com/apaquette/ETLRelay/actions/runs/39635472040)
was inspected through GitHub's public run and job records. Each listed job
completed successfully:

| Declared combination | Baseline evidence |
| --- | --- |
| Ubuntu / CPython 3.12 | [Quality, full suite, packaging, installed wheel](https://github.com/apaquette/ETLRelay/actions/runs/39635472040/job/119344625828) |
| Ubuntu / CPython 3.13 | [Installed-wheel smoke](https://github.com/apaquette/ETLRelay/actions/runs/39635472040/job/119345318931) |
| Ubuntu / CPython 3.14 | [Installed-wheel smoke](https://github.com/apaquette/ETLRelay/actions/runs/39635472040/job/119345318992) |
| macOS / CPython 3.12 | [Installed-wheel smoke](https://github.com/apaquette/ETLRelay/actions/runs/39635472040/job/119345318707) |
| Windows / CPython 3.12 | [Installed-wheel smoke](https://github.com/apaquette/ETLRelay/actions/runs/39635472040/job/119345318978) |

These are evidence for the baseline, not successful CI results for this change.
The revised script and dependency metadata subsequently passed the same jobs
after integration, as recorded below. Local Linux results alone would not
establish macOS/Windows source-install success.

Support is the five combinations above, not a full operating-system/Python
Cartesian product. Other interpreters, OS releases, architectures, and database
dialects are not independently verified. The getting-started prerequisite now
states the bounded Python range instead of claiming all Python versions newer
than 3.12.

## Reproducible checks

Install development, documentation, and CI tools, then build/check archives:

```bash
uv sync --locked --all-groups
uv lock --check
uv audit --locked --preview-features audit-command
uv pip check --python .venv/bin/python
uv build
uvx --from 'twine>=7,<8' twine check dist/*
uv run python tests/packaging/check_distributions.py
```

Use each interpreter without changing the primary development environment:

```bash
uv python install 3.12 3.13 3.14
uv run --no-project --python 3.12 python tests/packaging/smoke_compatibility.py dist
uv run --no-project --python 3.13 python tests/packaging/smoke_compatibility.py dist
uv run --no-project --python 3.14 python tests/packaging/smoke_compatibility.py dist
```

The default is `--artifact both`; use `--artifact wheel` or `--artifact sdist`
for a targeted retry. Each selected artifact gets its own fresh environment and
working directory. Python inspection uses `-I`, checks import paths/version,
and verifies that no repository directory is present in `sys.path`.

Run the ordinary full test suite, coverage gate, Ruff lint/format, Pyright, and
strict MkDocs build as required by the release checklist. Existing installed-CLI
functional tests continue to exercise richer CSV, Parquet, SQLite, and failure
workflows without being duplicated throughout the platform matrix.

## Local verification results

The working change was verified on Linux x86_64 with uv 0.12.23:

| Interpreter | Wheel install/API/CLI | Sdist build/install/API/CLI |
| --- | --- | --- |
| CPython 3.12.14 | Passed | Passed |
| CPython 3.13.16 | Passed | Passed |
| CPython 3.14.8 | Passed | Passed |

Additional checks:

- Full unit/integration/functional suite on CPython 3.12.14: **734 passed**.
- Configured statement/branch coverage: **100%**.
- Nine dependency-metadata regression cases: passed.
- Wheel and source-distribution builds, Twine, and archive checks: passed.
- Lockfile check and installed dependency consistency: passed.
- Dependency audit: no known vulnerabilities; one existing archived-project
  status for the documentation dependency `verspec` was reported.
- Ruff lint/format, Pyright, strict documentation build, and diff checks: passed.

## Acceptance status

- [x] Wheel and source distribution build and archive checks pass.
- [x] Both artifacts install outside the checkout and exercise public APIs/CLI.
- [x] Runtime metadata reflects the frozen implementation and exact constraints.
- [x] Full local tests and required quality checks pass.
- [x] Baseline CI evidence exists for all five declared combinations.
- [x] Revised wheel/sdist checks and dependency metadata pass all five CI jobs at commit `4930087`.

The integrated packaging verification gate is satisfied by the run below. Later
changes and final release artifacts still require their own required CI checks.


## Integrated CI confirmation

On 2026-10-21, GitHub reported
[CI run 39637775631](https://github.com/apaquette/ETLRelay/actions/runs/39637775631)
completed successfully for commit `493008769ae5ca60daf4b2454c35d635e1793c5b`.
All five required jobs passed:

| Combination | Wheel and sdist CI evidence |
| --- | --- |
| Ubuntu / CPython 3.12 | [Quality](https://github.com/apaquette/ETLRelay/actions/runs/39637775631/job/119352913973) |
| Ubuntu / CPython 3.13 | [Compatibility](https://github.com/apaquette/ETLRelay/actions/runs/39637775631/job/119353646228) |
| Ubuntu / CPython 3.14 | [Compatibility](https://github.com/apaquette/ETLRelay/actions/runs/39637775631/job/119353646054) |
| macOS / CPython 3.12 | [Compatibility](https://github.com/apaquette/ETLRelay/actions/runs/39637775631/job/119353646188) |
| Windows / CPython 3.12 | [Compatibility](https://github.com/apaquette/ETLRelay/actions/runs/39637775631/job/119353646599) |

This closes the prior packaging ticket's pending CI evidence requirement. It
verifies the packaging source state, not subsequent documentation changes or a
future versioned beta publication.
