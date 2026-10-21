# v0.9.0 Release Verification

Target: **v0.9.0 — Feature-complete beta**, **2026-10-21**.
Review record: `docs/development/beta-readiness.md`.

Checked items describe completed review/local checks. Unchecked CI/publication
items must be completed by the existing release process; they are not claims of
an unresolved implementation gap. If publication moves, update the changelog and
release-note date before promotion. Earlier release checklists remain in Git history.

## Feature and API review

- [x] Tickets 0.9.0-01 through 0.9.0-07 are closed and integrated at `1b0993b`.
- [x] Required v1.0 inventory is implemented; deferred work is excluded.
- [x] Tabular protocols, public API, schema, exceptions, transactions, and ownership are reviewed.
- [x] Pipeline and failure matrices map to meaningful automated tests.
- [x] Documentation, executable examples, migration guide, and release notes are complete.
- [x] Public open issues reviewed on 2026-10-21: only #37 and #139 remain; no separate unresolved defect found.
- [x] Known limitations, deferred work, feedback criteria, and defect-reporting/triage paths are documented.

## Release metadata

- [x] `pyproject.toml` and `uv.lock` identify `0.9.0`.
- [x] `requires-python` remains `>=3.12,<3.15`; `.python-version` selects 3.12.
- [x] README, documentation homepage, installation, CLI output examples, security policy, and roadmap reflect v0.9.0.
- [x] Release-content links use `v0.9.0` repository paths or `0.9.0` documentation paths; historical evidence stays immutable.
- [x] Changelog and release notes have the target date and describe breaking changes.
- [x] Existing release workflow uses the finalized version-specific notes for its GitHub release body; shell syntax and a stubbed `gh` dry run pass.

## Local dependency, quality, and distribution checks

Commands passed in the release-preparation checkout using Linux CPython 3.12.14.
The full suite reports **736 passed, 100% configured statement/branch coverage**.
The dependency audit exited successfully with no known vulnerabilities; it also
reported archived `verspec` (a transitive documentation dependency of `mike`).
This maintenance status is tracked in the readiness record; it is not a runtime
dependency or a reported vulnerability.

- [x] `uv lock --check` and `uv pip check --python .venv/bin/python` pass.
- [x] `uv audit --locked --preview-features audit-command` reports no known vulnerabilities.
- [x] `uv run pytest --cov=etlrelay --cov-branch --cov-report=term-missing --cov-fail-under=90.1 -q` passes, including installed examples/quick start.
- [x] `uv run ruff check src tests` and `uv run ruff format --check src tests` pass.
- [x] `uv run pyright` passes.
- [x] `uv run mkdocs build --strict` and `git diff --check` pass.
- [x] Fresh `uv build` wheel and sdist pass Twine and `tests/packaging/check_distributions.py`.
- [x] `tests/packaging/smoke_compatibility.py dist` installs both v0.9.0 artifacts outside the checkout and verifies public imports, direct CSV/Parquet/SQLite pipelines, CLI, and YAML.

## Integrated CI and support matrix

All five jobs passed for baseline `1b0993b1b5bc012754c5c3960c6b79f21d36f189`,
[run 39642253494](https://github.com/apaquette/ETLRelay/actions/runs/39642253494).
This establishes the integrated prerequisite evidence. Repeat for the final
v0.9.0 metadata/documentation/workflow change before promoting to `main`.

Final integrated commit and CI run: **record after integration**.

- [ ] Ubuntu / CPython 3.12: full suite, quality, docs, packaging, both-artifact smoke.
- [ ] Ubuntu / CPython 3.13: both-artifact smoke.
- [ ] Ubuntu / CPython 3.14: both-artifact smoke.
- [ ] macOS / CPython 3.12: both-artifact smoke.
- [ ] Windows / CPython 3.12: both-artifact smoke.
- [ ] Recheck newly opened issues; resolve any release-blocking defect before merge.

## Promotion and publication

Follow `docs/development/release-automation.md`; no new release mechanism is needed.

- [ ] Existing TestPyPI workflow on `dev` publishes and smoke-tests v0.9.0 successfully.
- [ ] Reviewed release commit is promoted from `dev` to `main` with required CI green.
- [ ] Production workflow verifies and publishes `etlrelay==0.9.0` to PyPI.
- [ ] Generated GitHub tag/release `v0.9.0` targets the released commit and uses finalized release notes.
- [ ] Versioned documentation under `/ETLRelay/0.9.0/` is accessible and pinned example/policy links resolve.
- [ ] Published artifacts, version metadata, release text, and documentation agree.
- [ ] Close #139 and parent #37 after their completion criteria are satisfied; record actual beta feedback separately.
