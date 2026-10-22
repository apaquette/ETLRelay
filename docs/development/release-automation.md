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

ETLRelay retains the existing branch and publication strategy.
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
6. Verify that community documentation, including `CONTRIBUTING.md`,
   `CODE_OF_CONDUCT.md`, `ACCESSIBILITY.md`, and the GitHub issue and
   pull request templates, is complete and internally consistent.
7. Run the dependency audit and installed dependency compatibility checks.
8. Run the full tests, coverage, lint, formatting, type-checking,
   and strict documentation build.
9. Build a fresh wheel and source distribution.
10. Validate the built artifacts using Twine and the distribution
    verification script.
11. Verify clean-environment installation, CLI behavior, and a
    representative pipeline execution using both built artifacts.
12. Confirm the complete CI workflow and compatibility matrix pass.
13. Review the changeset for unintended public API changes,
    dependency changes, unsupported security claims, or out-of-scope work.
14. Complete the release checklist before promoting `dev` to `main`.

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

### Installed-artifact compatibility

The compatibility jobs download the same wheel and source distribution built by the quality job.
The sdist is built in an isolated installation environment; the source checkout
is never installed as a substitute.

| Platform | Python |
|---|---|
| Ubuntu | 3.13 |
| Ubuntu | 3.14 |
| macOS | 3.12 |
| Windows | 3.12 |

Each compatibility job installs each artifact into a separate clean environment,
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
declared metadata. Wheel and source-distribution smoke tests independently verify
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

TestPyPI provides a staging environment for validating release artifacts
before publication to production PyPI.

1. Merge the release candidate into `dev` and confirm CI passes.
2. In GitHub Actions, select **Publish to TestPyPI**, choose the `dev`
   branch, and manually run the workflow.
3. Verify the release candidate passes dependency checks, full tests,
   coverage, linting, formatting, type checking, and strict documentation
   validation.
4. Verify that the wheel and source distribution are built and checked
   for correct metadata, package contents, and installed-package behavior.
5. Publish the verified distribution artifacts to TestPyPI using
   the configured Trusted Publisher.
6. Install the published package into an isolated environment, with runtime
   dependencies supplied from PyPI.
7. Verify package imports, installed version, dependency consistency,
   CLI availability, YAML validation, and a representative CSV pipeline.
8. Review the complete workflow results and TestPyPI package page before
   promoting the release candidate to `main`.

TestPyPI is independent of the production `PYPI_RELEASE_ENABLED` setting.
Running its workflow does not enable production publication.

TestPyPI versions are immutable. If the target version already exists,
use an appropriate new prerelease version for another publication attempt
or inspect the existing published artifacts.

The release candidate must not be considered verified if post-publication
smoke testing fails.

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

Production publication is separate from TestPyPI verification. With
`PYPI_RELEASE_ENABLED` set to `true`, merging a previously unpublished
package version into `main` can initiate publication automatically.

The release workflow creates the GitHub tag and release only after
successful package publication. Do not create the release tag manually
before this workflow unless performing an explicitly documented recovery.

The GitHub release description is generated by the workflow using
GitHub's automatic release-note generation. The project changelog
remains the maintained record of release changes.

Versioned documentation is deployed separately after successful
package publication, with the new release version becoming the
documentation site's `latest` alias.

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

The shared compatibility smoke script now defaults to testing both artifacts
in separate environments. TestPyPI and PyPI verification workflows use this
same script before publication. See the
[packaging verification record](packaging-verification.md) for commands and evidence.


## v1.0.1 documentation-only patch release

ETLRelay v1.0.1 is a documentation-only maintenance release that
introduces community contribution guidelines, a Code of Conduct,
an accessibility statement, and standardized GitHub issue and
pull request templates.

The release preserves the stable public Python interfaces,
CLI behavior, YAML configuration schema version `1`, dependencies,
and operational contracts established in v1.0.0.

No Python or YAML migration is required from v1.0.0.

### Release preparation

1. Update `pyproject.toml` to version `1.0.1` and synchronize `uv.lock`.
2. Add the v1.0.1 entry to `CHANGELOG.md`.
3. Update current-release references in the README and documentation homepage.
4. Verify the new Community Standards documents and GitHub templates.
5. Confirm all versioned documentation links target `1.0.1`,
   except links intentionally referring to historical releases.
6. Run the full quality suite, strict documentation build,
   dependency checks, and distribution verification.
7. Verify the built wheel and source distribution in separate
   clean environments outside the repository checkout.
8. Confirm the complete GitHub Actions compatibility matrix passes.

Documentation-only changes do not exempt the release from the
existing packaging and compatibility verification requirements.

### TestPyPI and production promotion

Use the existing manually triggered TestPyPI workflow on `dev`
to verify the release candidate.

Review the successful build, publication, and installed-package
smoke-test results before opening the release pull request
from `dev` into `main`.

When production publication is enabled, merging a new package
version into `main` triggers the existing release workflow.

For v1.0.1, the expected release artifacts are:

- PyPI package: `etlrelay==1.0.1`
- Git tag: `v1.0.1`
- GitHub release: `ETLRelay 1.0.1`
- Versioned documentation: `1.0.1`
- Documentation alias: `latest` points to `1.0.1`

The production workflow creates the release tag after successful
package publication. Do not create the tag in advance.

The v1.0.0 release notes and readiness records remain historical
documentation and must not be rewritten as v1.0.1 release evidence.

### Release verification

Complete `RELEASE_CHECKS.md` against the v1.0.1 release candidate.

After publication, independently confirm:

1. The v1.0.1 wheel and source distribution are available on PyPI.
2. The published package installs and reports version `1.0.1`.
3. The GitHub `v1.0.1` release and tag reference the intended commit.
4. Versioned documentation is accessible under `/ETLRelay/1.0.1/`.
5. The Community Standards files are present and recognized by GitHub.
6. The documentation homepage, README, and changelog reflect v1.0.1.

Do not mark publication complete solely because a local build or
TestPyPI verification succeeded.
