## v0.9.0 documentation review

Local evidence is recorded in `docs/development/documentation-review.md`.

- [x] Candidate versus published installation and bounded support are explicit.
- [x] Quick-start CSV/YAML/Python snippets execute against an isolated candidate wheel.
- [x] Five Python examples, nine YAML configurations, and representative Python-runner examples pass with data/schema assertions.
- [x] Migration, draft release notes, contribution guidance, and known limitations are documented.
- [x] Full local suite: 736 passed, 100% configured coverage; strict documentation and quality checks pass.
- [ ] Integrated documentation change passes required CI.
- [ ] Beta preparation assigns the release version/date and finalizes published links and release notes.

## v0.9.0 packaging and compatibility gate

Local evidence for the packaging change is recorded in
`docs/development/packaging-verification.md`. The v0.8.0 checklist below is
retained as historical release context. The integrated packaging source
`4930087` passed CI run `39637775631` across all five combinations.

- [x] Wheel/sdist metadata, dependency bounds, modules, licence, notice, and entry-point checks pass locally.
- [x] Both artifacts install outside the checkout on Linux CPython 3.12, 3.13, and 3.14.
- [x] Public imports, direct CSV/Parquet/SQLite pipelines, YAML validation, and CLI execution pass.
- [x] Full local suite: 734 passed, 100% configured coverage; required quality checks pass.
- [x] Ubuntu / Python 3.12 required CI passes for the integrated packaging change.
- [x] Ubuntu / Python 3.13 wheel and sdist smoke passes for that change.
- [x] Ubuntu / Python 3.14 wheel and sdist smoke passes for that change.
- [x] macOS / Python 3.12 wheel and sdist smoke passes for that change.
- [x] Windows / Python 3.12 wheel and sdist smoke passes for that change.
- [x] Record the integrated commit and successful CI run in the verification record.


## v0.8.0 release verification

### Release metadata

- [ ] `pyproject.toml` declares version `0.8.0`.
- [ ] `uv.lock` matches the final project metadata.
- [ ] `requires-python` is `>=3.12,<3.15`.
- [ ] `.python-version` selects Python 3.12.
- [ ] README, documentation index, and changelog describe v0.8.0.
- [ ] Version-specific documentation links target v0.8.0.

### Dependency and quality checks

- [ ] `uv lock --check` passes.
- [ ] `uv audit --locked --preview-features audit-command` reports no
      known vulnerabilities.
- [ ] `uv pip check --python .venv/bin/python` passes.
- [ ] Full pytest suite and configured coverage gate pass.
- [ ] Ruff lint and formatting checks pass.
- [ ] Pyright passes.
- [ ] `uv run mkdocs build --strict` passes.
- [ ] `git diff --check` passes.

### Distribution checks

- [ ] Fresh wheel and source distribution build successfully.
- [ ] Twine validates both artifacts.
- [ ] `tests/packaging/check_distributions.py` passes.
- [ ] Built artifacts contain the expected project version and modules.
- [ ] Installed-wheel import isolation succeeds.
- [ ] Installed CLI version and help output succeed.
- [ ] Installed YAML validation and CSV pipeline execution succeed.
- [ ] Selected error-code and sensitive-output regressions pass.

### Compatibility

- [ ] Ubuntu / Python 3.12 quality job passes.
- [ ] Ubuntu / Python 3.13 wheel smoke passes.
- [ ] Ubuntu / Python 3.14 wheel smoke passes.
- [ ] macOS / Python 3.12 wheel smoke passes.
- [ ] Windows / Python 3.12 wheel smoke passes.

### Security and operational review

- [ ] Security documentation matches the tested controls.
- [ ] Path containment is not described as a complete sandbox.
- [ ] SQL configuration validation is not described as authorization.
- [ ] Logging protection is limited to ETLRelay-controlled diagnostics.
- [ ] File overwrite and partial-write limitations are documented.
- [ ] SQL per-batch transactions and rollback limitations are documented.
- [ ] Resource ownership and cleanup responsibilities are documented.
- [ ] Unsupported and deferred capabilities are recorded.
- [ ] No unrelated implementation refactoring was introduced.

### Publication

- [ ] Release candidate is merged and required CI checks pass.
- [ ] TestPyPI verification is completed if required for this release.
- [ ] Production publishing workflow succeeds.
- [ ] PyPI contains `etlrelay==0.8.0`.
- [ ] GitHub tag and release `v0.8.0` exist.
- [ ] Versioned documentation for `0.8.0` is accessible.
- [ ] Final release notes match the published artifacts.
