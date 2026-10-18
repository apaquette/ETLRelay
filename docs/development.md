# Development

ETLRelay uses Python 3.12+, Nix flakes for a reproducible development environment, `uv` for Python dependencies and lockfiles, pytest for tests, Ruff for linting and formatting, Pyright for static typing, MkDocs for documentation, GitHub Actions for CI, and PyPI for distribution.

## Install the development environment

From the repository root, synchronize the committed lockfile and all dependency groups:

```bash
uv sync --locked --all-groups
```

Run checks in the project's supported Nix development environment when tools such as Ruff or Pyright are supplied by Nix rather than the Python environment. Do not change runtime dependencies solely to make a development tool available.

## Run quality checks

Run the repository's configured tests and quality checks:

```bash
uv run pytest --cov=etlrelay --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=90.1
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run mkdocs build --strict
```

The configured coverage gate requires at least 90.1% reported coverage. If a known static-analysis command fails because of an existing environment or baseline issue, record its exact diagnostic and compare it with the established baseline rather than silently treating it as a pass.

For a release candidate, also build and validate the distributions:

```bash
uv build
uvx --from 'twine>=7,<8' twine check dist/*
```

Follow `docs/development/release-automation.md` and `RELEASE_CHECKS.md` for the complete release process and result-recording requirements.

## Preview documentation

Start the local documentation server from the repository root:

```bash
uv run mkdocs serve
```

MkDocs serves a preview and rebuilds pages when documentation files change. Review changed pages in the rendered site, including Mermaid diagrams and navigation links.

## Validate documentation

Build the documentation with warnings treated as errors:

```bash
uv run mkdocs build --strict
```

The build output is written to `site/`. Do not commit generated `site/` files; ensure `site/` is listed in `.gitignore`.

The API reference uses `mkdocstrings` to render the documented modules from `src/`. When a module path or public API changes, update `docs/api-reference.md` and any affected user-facing or architecture pages, then ensure the strict build passes.
