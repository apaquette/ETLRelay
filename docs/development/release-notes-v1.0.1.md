# ETLRelay v1.0.1 — Community Standards and Contribution Guidance

Release date: **Pending publication**.

ETLRelay v1.0.1 is a documentation-only patch release that builds on the
stable public contracts established in v1.0.0. It introduces community
contribution guidelines, a Code of Conduct, an accessibility statement,
and standardized GitHub issue and pull request templates.

These additions improve contributor onboarding, issue reporting, and
community participation while preserving the existing runtime behavior,
public APIs, YAML configuration schema, CLI functionality, and
dependency requirements.

## What's Changed

### Community Standards

- Add [Code of Conduct](https://github.com/apaquette/ETLRelay/blob/v1.0.1/CODE_OF_CONDUCT.md)
  based on the Contributor Covenant, establishing community participation
  expectations, private reporting procedures, and enforcement guidelines.
- Add [Contribution Guidelines](https://github.com/apaquette/ETLRelay/blob/v1.0.1/CONTRIBUTING.md)
  covering development setup, branch workflows, test-driven development,
  quality checks, architecture guidelines, and pull request requirements.
- Add an [Accessibility Statement](https://github.com/apaquette/ETLRelay/blob/v1.0.1/ACCESSIBILITY.md)
  documenting accessibility considerations for the documentation, CLI,
  and contribution process, including known limitations and feedback
  procedures.
- Establish clearer distinctions between community conduct reports,
  public bug reports, feature requests, and private security
  vulnerability disclosures.

### GitHub Issue and Pull Request Templates

- Add a bug report template requesting reproduction steps, expected and
  actual behavior, environment information, and relevant diagnostics.
- Add a feature request template covering use cases, proposed behavior,
  alternatives, and compatibility considerations.
- Add a pull request template covering change summaries, tests,
  documentation, compatibility, and security implications.
- Direct security vulnerability reports to the private disclosure
  procedure rather than public GitHub issues.
- Align contribution templates with the project's `dev` integration
  branch and `main` release branch workflow.

### Documentation

- Update the README and documentation homepage to describe v1.0.1
  and link to the new Community Standards resources.
- Update the development guide to reference the contribution
  guidelines and clarify contributor expectations.
- Update release automation documentation to include Community
  Standards verification and documentation-only patch release procedures.
- Update the security policy to reference v1.0.1, preserve the existing
  vulnerability reporting process, and distinguish security reports
  from community conduct reports.
- Update the changelog, installation examples, and versioned
  documentation links for v1.0.1.
- Preserve the v1.0.0 release notes and readiness records as
  historical documentation.

## Upgrading

Applications using v1.0.0 require no Python or YAML migration.

ETLRelay v1.0.1 introduces no changes to:

- Public Python interfaces, constructors, or protocols.
- YAML configuration schema version `1`.
- CLI commands, arguments, or exit codes.
- Source, processor, sink, reader, or writer behavior.
- Schema validation, error propagation, or resource ownership.
- Filesystem and SQL persistence semantics.
- Runtime dependencies or supported Python versions.

Install the patch release with:

```bash
python -m pip install etlrelay==1.0.1
```

For the stable public contract, see the
[compatibility policy](../compatibility.md) and
[v1.0.0 release notes](release-notes-v1.0.0.md).

Applications upgrading from releases before v0.9.0 should also review the
[v0.9.0 migration guide](migration-v0.9.0.md).

## Contributing

Contributions to ETLRelay are welcome, including bug fixes,
documentation improvements, additional tests, and focused feature
proposals.

Before contributing, review the
[Contribution Guidelines](https://github.com/apaquette/ETLRelay/blob/v1.0.1/CONTRIBUTING.md)
and the project's
[Code of Conduct](https://github.com/apaquette/ETLRelay/blob/v1.0.1/CODE_OF_CONDUCT.md).

Bug reports and feature requests can be submitted through
[GitHub Issues](https://github.com/apaquette/ETLRelay/issues/new/choose).

Significant new capabilities and architectural changes should be
discussed before implementation and evaluated against the
[post-v1.0 roadmap](../roadmap.md#post-v100-roadmap).

Suspected security vulnerabilities must be reported privately through
the [Security Policy](https://github.com/apaquette/ETLRelay/blob/v1.0.1/SECURITY.md).

## Support and Known Limitations

ETLRelay v1.0.1 retains the support matrix established in v1.0.0:

| Platform | Python | Verification |
|---|---|---|
| Ubuntu | 3.12 | Full test suite and installed-artifact verification |
| Ubuntu | 3.13 | Installed wheel and source-distribution verification |
| Ubuntu | 3.14 | Installed wheel and source-distribution verification |
| macOS | 3.12 | Installed wheel and source-distribution verification |
| Windows | 3.12 | Installed wheel and source-distribution verification |

SQLite remains the reference SQL integration-test backend. Other
SQLAlchemy dialects require appropriate drivers and independent
verification.

Existing operational limitations remain unchanged:

- Local filesystem writes are non-atomic and may leave partial output.
- SQL sinks append to existing tables using per-batch transactions;
  previously committed batches are not rolled back by later failures.
- SQL source results are materialized in memory.
- Local filesystem path containment does not provide a complete sandbox.
- ETLRelay-controlled logging does not guarantee sanitization of
  arbitrary third-party exceptions or application logs.
- Remote storage, additional formats and processors, dynamic plugins,
  scheduling, retries, and distributed execution remain outside the
  current supported feature set.

This release introduces no additional runtime functionality and does
not change these limitations.

For implementation details, see the
[scope policy](v1-scope.md),
[API reference](../api-reference.md),
[security guidance](../security.md), and
[compatibility policy](../compatibility.md).

## Release Verification

As a documentation-only patch, v1.0.1 retains the existing release
verification requirements.

Release acceptance includes:

- Strict MkDocs documentation validation.
- Dependency lockfile and vulnerability checks.
- Full pytest, Ruff, and Pyright verification.
- Wheel and source-distribution metadata and content checks.
- Clean-environment installed-artifact compatibility testing.
- Verification of the unchanged public API, CLI, and YAML contracts.
- Review of Community Standards files, GitHub templates, and
  version-specific documentation links.
- Successful TestPyPI verification and production release workflows.

No runtime implementation or dependency changes are required for this patch.

The v1.0.0 release established the stable runtime baseline; v1.0.1
extends the repository's community and documentation infrastructure
without altering that baseline.