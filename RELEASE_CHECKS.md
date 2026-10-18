# Release Automation and Readiness

Use this checklist when preparing a tagged ETLRelay release. Record the actual result for the current checkout; do not mark a check passed based on an earlier release's result.

## v0.6.0 documentation and release pass

The v0.6.0 feature and package checks have already been run for the implementation ticket. After modifying documentation, rerun the strict documentation build because links, navigation, code examples, and generated API references may have changed.

From the repository root, within the project's supported development shell/environment:

```bash
uv sync --locked --all-groups
uv run pytest --cov=etlrelay --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=90.1
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run mkdocs build --strict
uv build
uvx --from 'twine>=7,<8' twine check dist/*
```

Preserve any known unrelated baseline failure with its exact diagnostic and demonstrate whether it changes relative to the pre-ticket baseline.

## Content review

- `docs/configuration.md` is the canonical schema reference and matches schema version 1.
- Every YAML example loads and builds through `ConfigLoader`, the default component catalog, and `PipelineBuilder`.
- Examples cover the four file-to-file format pairs, file-to-SQL, SQL-to-file, and SQL-to-SQL combinations.
- Secret values are not embedded in YAML; SQL error messages do not expose resolved URLs.
- Architecture pages describe implemented class names and signatures rather than planned designs.
- README, documentation site, changelog, package version, release tag, and versioned links consistently identify v0.6.0.
- The documentation build checks all MkDocs nav entries and internal links.

## Distribution checks

After `uv build`, test the wheel and source distribution in a clean environment using the repository's established smoke-test procedure. Verify configuration modules, YAML reader, dependencies, and component builder imports are present in the built artifact, rather than relying only on imports from the repository checkout.

Confirm `pyproject.toml`, lock metadata where applicable, Git tag, changelog, release notes, and built distribution names/versions agree before publication.

## Results record

| Check | Result for final docs revision | Notes |
|---|---|---|
| Locked dependency sync | Not run by this documentation bundle | Record result from project checkout. |
| Full test suite and coverage | Implementation ticket passed before docs edits | Re-run if executable examples or package files change. |
| Ruff lint | Implementation ticket passed before docs edits | Re-run as part of release check. |
| Ruff format | Implementation ticket passed before docs edits | Re-run as part of release check. |
| Pyright | Implementation ticket baseline documented | Record exact current result and compare with baseline. |
| Strict MkDocs build | Must be run after these documentation edits | Critical for nav, cross-links, and mkdocstrings paths. |
| Source/wheel build | Implementation ticket passed before docs edits | Re-run if packaging metadata or packaged examples change. |
| Twine validation | Implementation ticket passed before docs edits | Use the project's locked/current tool constraint. |
| Clean artifact install/smoke test | Implementation ticket passed before docs edits | Check configuration modules and dependencies. |
