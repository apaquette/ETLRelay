# CI and Release Automation

This document describes the intended ETLRelay branch and publishing workflow.

## Branch strategy

- `dev` is the integration branch for active development.
- Work-in-progress changes are developed on feature branches and merged into `dev` through pull requests, or committed directly to `dev` if working solo and that is the chosen project practice.
- A release is promoted by opening a pull request from `dev` into `main`.
- `main` is the production branch. A push to `main` triggers the PyPI release workflow.
- The release workflow publishes only when the version in `pyproject.toml` has not already been published to PyPI. Merging ordinary changes without a version bump therefore does not create a duplicate release.

Before a release PR is merged:

1. Update `project.version` in `pyproject.toml`.
2. Update `CHANGELOG.md` to record the release.
3. Run all checks locally and ensure CI passes.
4. Confirm the release version and distribution name are correct.

A PyPI version cannot be overwritten. Every release that should publish must use a new version.

## Coverage requirement

CI runs pytest with line and branch coverage and requires coverage to be strictly greater than 90% (`90.1%` minimum reported coverage). The build fails if the threshold is not met. The coverage configuration is in `pyproject.toml`; see `snippets/coverage-config.toml` in the supplied setup bundle if those settings need to be added.

`pytest-cov` must be available in a development dependency group. Ruff and Pyright must also be available in a dependency group installed by CI. If they are only supplied by the local Nix development shell, add them to a CI-only dependency group so GitHub-hosted runners can run the same checks without installing the local Nix shell.

For example, add the following key to the existing `[dependency-groups]` table if these tools are not already supplied by one of its groups:

```toml
ci = [
    "ruff>=0.13,<1",
    "pyright>=1.1,<2",
]
```

Then regenerate `uv.lock` with `uv lock` and commit both files.

## GitHub branch protection

In repository settings, protect `main`:

- Require pull requests before merging.
- Require the `CI / quality` status check to pass.
- Require branches to be up to date before merging, if preferred.
- Block force pushes and deletion.

Protect `dev` from accidental deletion and force pushes as appropriate. If you require pull requests into `dev`, also require `CI / quality` there.

Configure the GitHub `pypi` environment to allow deployments from `main` only. Keep the production publishing job separate from the build job; only the publishing job receives `id-token: write`.

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

## First-release bootstrap order

The TestPyPI workflow must exist on GitHub's default branch before `workflow_dispatch` can be run. The production workflow is therefore gated during the first release so the initial merge cannot publish before TestPyPI verification. Use this order:

1. Set the repository Actions variable `PYPI_RELEASE_ENABLED` to `false` (or leave it unset).
2. Merge the release candidate from `dev` into `main`, including the CI/release workflow files. The production workflow is present but disabled, so this merge does not publish to PyPI.
3. Configure the TestPyPI Trusted Publisher and GitHub `testpypi` environment. Run **Publish to TestPyPI** with the selected branch set to `dev`, then wait for its smoke-test job to pass.
4. Configure the PyPI Trusted Publisher and the GitHub `pypi` environment. Review the successful TestPyPI run and release notes.
5. Set `PYPI_RELEASE_ENABLED` to `true`, then manually run **Publish release to PyPI** with the selected branch set to `main`. This publishes the initial `0.1.0` and creates the matching GitHub tag/release. Leave the variable enabled for future releases.

The variable is a one-time bootstrap gate, not a permanent manual release step. After the first verified release, every push to `main` can publish automatically when `pyproject.toml` contains a new version. Manual production workflow dispatch is restricted to `main`.

## Production publication behavior

When `PYPI_RELEASE_ENABLED` is exactly `true`, every push to `main` runs `.github/workflows/release-pypi.yml`. It reads the project name/version and checks whether that exact version exists on PyPI.

- If it already exists, publication is skipped. This is expected for ordinary main-branch changes that do not bump the version.
- If it is new, the workflow runs the quality gates, builds the wheel and source distribution, checks the artifacts, publishes them to PyPI, and then creates a matching `vX.Y.Z` GitHub release/tag.
- If quality gates or publishing fail, no GitHub release is created.

The CI and release workflows both run checks intentionally: CI blocks unsafe merges, while the release workflow independently verifies the exact code and artifacts it publishes.

## Manual release recovery

If publication succeeds but GitHub release creation fails, do not change the published package version. Check whether the `vX.Y.Z` tag already exists and create the missing GitHub release manually for that same tag/commit. If the PyPI version exists but is wrong, publish a new version; PyPI files cannot be replaced in place.
