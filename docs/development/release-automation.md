# CI and Release Automation

ETLRelay uses GitHub Actions to verify changes, build and validate
distributions, publish releases to PyPI, and deploy versioned
documentation.

The CI workflow verifies dependency integrity, package metadata,
distribution contents, installed CLI behavior, and compatibility with
the supported Python versions and selected operating systems.

The production release workflow publishes a new version from `main`
when publishing is enabled and that exact version has not already
been released to PyPI.

ETLRelay v0.8.0 retains the existing branch and publication strategy.
The release-readiness checks verify the built distribution rather than
relying solely on editable development installations.

## Branch strategy

- `dev` is the integration branch for active development.
- Work-in-progress changes are developed on feature branches and merged into `dev` through pull requests, or committed directly to `dev` if working solo and that is the chosen project practice.
- A release is promoted by opening a pull request from `dev` into `main`.
- `main` is the production branch. A push to `main` triggers the PyPI release workflow when the release gate is enabled.
- The release workflow publishes only when the version in `pyproject.toml` has not already been published to PyPI. Merging ordinary changes without a version bump therefore does not create a duplicate release.

## Release candidate preparation

Before opening or merging a release pull request:

1. Set `project.version` in `pyproject.toml` to the intended release version.
2. Regenerate `uv.lock` and verify it with `uv lock --check`.
3. Confirm the supported Python range and default development interpreter.
4. Update `CHANGELOG.md` with the actual release changes.
5. Update the README, documentation homepage, and versioned links.
6. Run the dependency audit and installed dependency compatibility checks.
7. Run the full tests, coverage, lint, formatting, type-checking,
   and strict documentation build.
8. Build a fresh wheel and source distribution.
9. Validate the built artifacts using Twine and the distribution
   verification script.
10. Verify clean-environment installation, CLI behavior, and a
    representative pipeline execution using the built wheel.
11. Confirm the complete CI workflow and compatibility matrix pass.
12. Review the changeset for unintended public API changes,
    unsupported security claims, or out-of-scope refactoring.
13. Complete the release checklist before promoting `dev` to `main`.

A successful editable install does not satisfy the built-artifact
verification requirement.

PyPI versions cannot be overwritten. Release candidates must use an
appropriate new version when a previously published artifact needs
to be replaced.


## Continuous integration

The primary CI workflow is `.github/workflows/ci.yml`.

### Quality job

The primary quality job runs on Ubuntu with Python 3.12.

It verifies:

1. Dependency lockfile consistency using `uv lock --check`.
2. Known dependency vulnerabilities and adverse package statuses using
   `uv audit`.
3. Installed dependency compatibility using `uv pip check`.
4. The full pytest suite with statement and branch coverage.
5. Ruff linting and formatting.
6. Pyright static analysis.
7. Strict MkDocs documentation builds.
8. Wheel and source-distribution construction.
9. Distribution metadata using Twine.
10. Distribution contents through `tests/packaging/check_distributions.py`.
11. Installed CLI behavior using a wheel installed into an independent
    environment outside the repository checkout.

The installed CLI verification includes version/help output, configuration
validation, local CSV pipeline execution, exit codes, and selected
sensitive-output regression checks.

The quality job uploads the verified distribution artifacts for use by
the compatibility matrix.

### Installed-wheel compatibility

The compatibility jobs download the same wheel built by the quality job.
They do not rebuild the project separately.

| Platform | Python |
|---|---|
| Ubuntu | 3.13 |
| Ubuntu | 3.14 |
| macOS | 3.12 |
| Windows | 3.12 |

Each compatibility job installs the wheel into a clean environment,
checks dependency consistency and import isolation, and exercises the
installed CLI and a minimal supported CSV pipeline.

The full pytest suite runs in the primary quality job rather than
being duplicated across every operating-system and Python combination.

### Verification limitations

The matrix does not test every possible operating-system, CPU
architecture, Python-version, or database-driver combination.

A successful dependency audit identifies no currently reported
vulnerabilities covered by the audit; it does not guarantee the absence
of undiscovered vulnerabilities.

Distribution metadata checks confirm expected archive contents and
declared metadata. Installed-wheel smoke tests independently verify
that representative runtime functionality works without the
repository checkout.


## Coverage requirement

CI runs pytest with line and branch coverage and requires coverage to be strictly greater than 90% (`90.1%` minimum reported coverage). The build fails if the threshold is not met. The coverage configuration is in `pyproject.toml`.

`pytest-cov` must be available in a development dependency group. Ruff and Pyright must also be available in a dependency group installed by CI. If they are only supplied by the local Nix development shell, add them to a CI-only dependency group so GitHub-hosted runners can run the same checks without installing the local Nix shell.

## GitHub branch protection

In repository settings, protect `main`:

- Require pull requests before merging.
- Require the `CI / quality` status check to pass.
- Require branches to be up to date before merging, if preferred.
- Block force pushes and deletion.

Protect `dev` from accidental deletion and force pushes as appropriate. If you require pull requests into `dev`, also require `CI / quality` there. Configure the GitHub `pypi` environment to allow deployments from `main` only. Keep the production publishing job separate from the build job; only the publishing job receives `id-token: write`.

## CLI release verification (v0.7.0 onward)

Before promoting a CLI release, verify the command boundary from the built package, not only from a repository checkout:

1. Run `uv run mkdocs build --strict` to catch broken navigation, missing pages, and documentation warnings.
2. Run the functional installed-package tests that build and install the wheel in an isolated environment.
3. Confirm `etlrelay --help`, `etlrelay help run`, and `etlrelay version` work from outside the repository checkout.
4. Validate a supported local CSV configuration, run it through `etlrelay run`, and inspect the generated output.
5. Verify validation does not create output and failures use the documented exit codes without printing sentinel credentials or payload values.
6. Run the project test suite, Ruff lint/format checks, Pyright, `uv build`, and distribution metadata validation.

Do not mark the release ready if the strict documentation build or clean-install/installed-CLI checks remain unverified. Record any genuine environment-specific limitation explicitly and distinguish it from a product or documentation failure.

## TestPyPI procedure

1. Merge the release candidate into `dev` and make sure CI passes.
2. In GitHub Actions, select **Publish to TestPyPI**, select the `dev` branch, and run the workflow manually.
3. The workflow runs tests, enforces coverage, checks lint/format/types, builds the docs and distributions, then publishes the built distributions to TestPyPI.
4. A smoke-test job creates a clean environment, installs runtime dependencies from PyPI, installs the ETLRelay package itself from TestPyPI, and checks core imports.
5. Review the workflow result and package page on TestPyPI before promoting the same version to production.

TestPyPI versions are also immutable. If a version was already uploaded to TestPyPI, use a new pre-release version for another publishing attempt, or inspect the existing uploaded artifact instead of trying to overwrite it.

## Configure Trusted Publishing

Create/configure Trusted Publishers separately on TestPyPI and PyPI. These values must match the repository that actually contains the workflows:

| Index | Workflow file | GitHub environment |
|---|---|---|
| TestPyPI | `.github/workflows/publish-testpypi.yml` | `testpypi` |
| PyPI | `.github/workflows/release-pypi.yml` | `pypi` |

For each index, configure the repository owner and repository name exactly. Configure the workflow filename and environment name to match the table. If the project has not yet been created on that index, use that index's pending Trusted Publisher flow for the first publication.

Trusted Publishing uses GitHub's OIDC integration, so do not add a long-lived PyPI API token to GitHub secrets. The publish jobs deliberately have only `id-token: write`; build and test jobs do not receive it.

## Production publication behavior

When `PYPI_RELEASE_ENABLED` is exactly `true`, every push to `main` runs `.github/workflows/release-pypi.yml`. It reads the project name/version and checks whether that exact version exists on PyPI.

- If it already exists, publication is skipped. This is expected for ordinary main-branch changes that do not bump the version.
- If it is new, the workflow runs the quality gates, builds the wheel and source distribution, checks the artifacts, publishes them to PyPI, and then creates a matching `vX.Y.Z` GitHub release/tag.
- If quality gates or publishing fail, no GitHub release is created.

The CI and release workflows both run checks intentionally: CI blocks unsafe merges, while the release workflow independently verifies the exact code and artifacts it publishes.

## Configuration documentation checks

For releases that change declarative configuration, include these documentation checks in the release review:

- `docs/configuration.md` must match the implemented schema version, component registrations, validator behavior, and SQL environment preflight.
- Runnable examples must use supported ETLRelay interfaces and remain
  consistent with the current release. Python configuration examples
  should use `ConfigLoader`, `create_default_component_catalog()`, and
  `PipelineBuilder` where appropriate. CLI examples should use the
  supported `etlrelay validate` and `etlrelay run` commands.
- Release verification must include the installed CLI smoke tests,
  confirming that configuration validation and pipeline execution
  work from a built distribution outside the repository checkout.
- README, getting-started, API reference, configuration architecture, security, changelog, roadmap, and versioned documentation links must consistently reflect the intended release.
- Run `uv run mkdocs build --strict` after documentation edits to check navigation, internal links, and generated API references.
- Run the release workflow's clean-environment smoke test against the built wheel and source distribution; do not rely only on imports from the repository checkout.

## Manual release recovery

If publication succeeds but GitHub release creation fails, do not change the published package version. Check whether the `vX.Y.Z` tag already exists and create the missing GitHub release manually for that same tag/commit. If the PyPI version exists but is wrong, publish a new version; PyPI files cannot be replaced in place.
