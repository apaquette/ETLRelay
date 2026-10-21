# Documentation setup and maintenance for ETLRelay

ETLRelay's documentation is built with MkDocs and Material for MkDocs. API reference pages use `mkdocstrings` to render documentation from the source tree, and Mermaid diagrams are enabled through the configured Markdown extensions. The documentation configuration lives in `mkdocs.yml`; published documentation pages live in `docs/`.

This document describes the current maintenance workflow. It is not a bootstrap procedure: do not add a second MkDocs configuration, copy a second `docs/` tree over the existing one, or add duplicate dependency groups.

## Install the project environment

From the repository root, synchronize the checked-in lockfile and all dependency groups:

```bash
uv sync --locked --all-groups
```

Keep documentation tooling in the existing documentation/development dependency groups rather than adding it to ETLRelay's runtime dependencies. If a command is supplied by the project's Nix development environment rather than by `uv`, run it from that environment and record any known baseline issue accurately.

## Edit documentation

- Add and edit user-facing pages in `docs/`.
- Update the navigation in `mkdocs.yml` when adding, removing, or renaming a page.
- Keep `docs/configuration.md` aligned with the implemented schema and supported component registrations.
- Keep `docs/api-reference.md` import paths aligned with the actual modules under `src/etlrelay`.
- Treat architecture diagrams as descriptions of implemented classes and contracts. Mark future possibilities as such, and do not present unimplemented storage backends or APIs as available features.
- Preserve relevant flow, data-flow, and class diagrams when updating an architecture page. Quote Mermaid node labels that contain punctuation which Mermaid could otherwise interpret as syntax.
- Keep executable examples consistent with configuration schema version 1 and test them against the current package where practical.

The site uses `pymdownx.superfences` for fenced code and Mermaid blocks. A Markdown file's presence on disk does not automatically add it to the navigation; update `mkdocs.yml` intentionally.

## Preview and validate

Preview the site locally:

```bash
uv run mkdocs serve
```

Build all documentation and treat warnings as errors:

```bash
uv run mkdocs build --strict
```

The generated site is written to `site/`. Do not commit generated `site/` output; ensure `site/` is ignored by Git.

A strict build checks MkDocs navigation, internal references, and API-reference resolution. It does not prove that each example is behaviorally correct or that every Mermaid diagram renders as intended, so review changed pages in the rendered preview as well.

## Documentation release check

For a release candidate, run the repository's full quality and packaging checks, including the strict documentation build. The current release checklist is maintained in `docs/development/release-automation.md` and `RELEASE_CHECKS.md`. Record results from the exact checkout intended for release; do not reuse a previous release's successful result as evidence for later documentation changes.

## Hosting and versioned documentation

The MkDocs configuration includes the `mike` plugin for versioned documentation. Use the repository's documented publishing workflow and verify the target branch, version, and hosting settings before deploying. Do not create a second deployment workflow or assume that a local build has published the site.

Release documentation must match the target package version, including
installation examples, CLI output, migration guidance, and release notes. During
preparation, record publication checks separately from local verification. Run
the installed-candidate example test in addition to the strict documentation build.

Pin release-content links to the target release: use the `v0.9.0` Git tag
for repository files and examples, and `/ETLRelay/0.9.0/` for absolute
documentation URLs. Do not link release content to moving branches such as
`dev` or `main`, or to a moving documentation alias such as `latest`. Relative
links between documentation pages stay within the deployed version. Keep
explicitly historical release links and immutable CI evidence tied to their
original versions or runs.
