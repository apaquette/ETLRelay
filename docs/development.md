# Development

ETLRelay uses the project's existing development stack: Python 3.12+, Nix flakes for the reproducible development environment, `uv` for Python dependencies and lockfiles, pytest for tests, Ruff for linting/formatting, Pyright for static typing, MkDocs for user-facing documentation, GitHub Actions for CI, and PyPI for distribution.

## Install development dependencies

From the repository root, after adding the documentation dependency group described in `DOCS_SETUP.md`:

```bash
uv sync --group docs
```

## Run quality checks

```bash
uv run pytest
ruff check .
ruff format --check .
pyright
```

Run these commands in the configured Nix development environment if Ruff and Pyright are provided by Nix rather than the Python environment.

## Preview documentation

```bash
uv run mkdocs serve
```

MkDocs serves a local preview and rebuilds pages when documentation files change.

## Validate documentation

```bash
uv run mkdocs build --strict
```

The build output is written to `site/`. Do not commit generated `site/` files; add `site/` to `.gitignore` if it is not already present.

The API reference page uses `mkdocstrings` to render documentation from the installed source tree. If a module path changes, update the API page to match the package structure and ensure a strict docs build passes.
