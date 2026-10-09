# MkDocs setup instructions for ETLRelay

The original ETLRelay technology plan selected MkDocs for documentation, `uv` for Python dependency management, GitHub Actions for CI, and PyPI for distribution. MkDocs was selected in the plan but is not yet configured in the current documentation set. This package adds a minimal setup using Material for MkDocs for the theme and `mkdocstrings[python]` for API reference generation from source docstrings.

## 1. Add documentation dependencies

From the repository root, run:

```bash
uv add --group docs "mkdocs>=1.6,<2" "mkdocs-material>=9,<10" "mkdocstrings[python]>=0.18,<1"
```

This should add a `docs` dependency group to `pyproject.toml` and update `uv.lock`. Keep these packages out of runtime dependencies.

Install the group:

```bash
uv sync --locked --group docs
```

## 2. Add the supplied files

Copy `mkdocs.yml` and the `docs/` directory from this package into the repository root. Add `CHANGELOG.md`, `NOTICE`, and `SECURITY.md` at the repository root if they do not already exist. Merge rather than overwrite any existing project configuration.

## 3. Ignore generated output

Add this line to the repository `.gitignore` if it is not already present:

```gitignore
site/
```

## 4. Build and preview

```bash
uv run mkdocs serve
uv run mkdocs build --strict
```

The API page references the expected `src/etlrelay` module layout. Review those import paths against the actual repository and fix any differences before considering the docs build complete.

## 5. Integrate with existing CI

Add this command to the existing GitHub Actions quality-check workflow after installing the `docs` dependency group:

```bash
uv run mkdocs build --strict
```

Do not create a duplicate CI workflow if an existing one already performs quality checks. A green strict build should be required for documentation changes.

## 6. Finish release documents

- `CHANGELOG.md`: move the initial-release entries under `[Unreleased]` to a `[0.1.0] - YYYY-MM-DD` heading with the actual release date when preparing the release tag.
- `NOTICE`: confirm the copyright holder and year, and ensure the notice is consistent with the existing `LICENSE` file.
- `SECURITY.md`: enable GitHub private vulnerability reporting before public release, or replace the reporting instructions with a verified private contact channel.
- Getting Started: run `examples/copy_csv.py` against the built and installed package. Correct the example if actual signatures differ.
- API reference: verify all paths listed in `docs/api-reference.md` exist in `src/etlrelay`.

## Hosting

MkDocs builds a static site in `site/`, which can be hosted on GitHub Pages or another static host. Hosting/deployment is intentionally not configured by this setup package because the repository URL, default branch, and GitHub Pages settings need to be confirmed in the actual repository. Add deployment after the strict local build passes.
