# v0.9.0 Release Verification — Completed

Target: **v0.9.0 — Feature-complete beta**, **2026-10-21**.
Review record: `docs/development/beta-readiness.md`.

Completed on 2026-10-21. This record combines the original local review
with final integrated CI and publication evidence; it does not modify the
published v0.9.0 tag or artifacts. External beta feedback is optional and is not
claimed to have been collected.

- Released commit: `d052986b3363bdb0d3b83d8f482d8a09b4a815e2`.
- [Final integrated CI](https://github.com/apaquette/ETLRelay/actions/runs/39649726342): all five jobs succeeded.
- [TestPyPI rehearsal](https://github.com/apaquette/ETLRelay/actions/runs/39648444904): succeeded on `dev` commit `d688e27af7dd621d343590f3e80149d25e5e11b2`.
- [Production release workflow](https://github.com/apaquette/ETLRelay/actions/runs/39649726279): verification, PyPI publication, GitHub release creation, versioned documentation, and Pages deployment succeeded.
- [PyPI](https://pypi.org/project/etlrelay/0.9.0/) contains the wheel and sdist; [GitHub release](https://github.com/apaquette/ETLRelay/releases/tag/v0.9.0) and [versioned documentation](https://apaquette.github.io/ETLRelay/0.9.0/) were verified.
- Tracker review for v1.0.0 found #139 and #37 closed, with only the new stable-release ticket #142 open.

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

All five jobs passed for released commit
`d052986b3363bdb0d3b83d8f482d8a09b4a815e2` in
[run 39649726342](https://github.com/apaquette/ETLRelay/actions/runs/39649726342).

- [x] Ubuntu / CPython 3.12: full suite, quality, docs, packaging, both-artifact smoke.
- [x] Ubuntu / CPython 3.13: both-artifact smoke.
- [x] Ubuntu / CPython 3.14: both-artifact smoke.
- [x] macOS / CPython 3.12: both-artifact smoke.
- [x] Windows / CPython 3.12: both-artifact smoke.
- [x] Recheck newly opened issues; resolve any release-blocking defect before merge.

## Promotion and publication

Follow `docs/development/release-automation.md`; no new release mechanism is needed.

- [x] Existing TestPyPI workflow on `dev` publishes and smoke-tests v0.9.0 successfully.
- [x] Reviewed release commit is promoted from `dev` to `main` with required CI green.
- [x] Production workflow verifies and publishes `etlrelay==0.9.0` to PyPI.
- [x] Generated GitHub tag/release `v0.9.0` targets the released commit and uses finalized release notes.
- [x] Versioned documentation under `/ETLRelay/0.9.0/` is accessible and pinned example/policy links resolve.
- [x] Published artifacts, version metadata, release text, and documentation agree.
- [x] #139 and parent #37 are closed; external beta participation is optional.
