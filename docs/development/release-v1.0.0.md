# v1.0.0 Stable Release Readiness

Ticket: [#142 — Release v1.0.0](https://github.com/apaquette/ETLRelay/issues/142).
Prepared from `dev` commit `d688e27af7dd621d343590f3e80149d25e5e11b2`.
Review and target release date: **2026-10-21**. Confirm the date before publishing.

## Release decision and scope

The v1.0.0 source is prepared from the officially released v0.9.0 feature set.
No required runtime feature remains incomplete and no open product defect was
found in the public issue review. The only open issue at review was #142;
prerequisite #139 and parent milestone #37 are closed. Repeat the issue check
before promotion.

This release changes metadata, policy, release records, and documentation.
Runtime source, tests, workflow definitions, runtime dependency bounds, and the
resolved third-party dependency versions are unchanged from the baseline.
There is no additional API change or YAML migration from v0.9.0.

The stable [compatibility policy](../compatibility.md) covers the documented
Python imports and signatures, tabular/schema semantics, YAML schema version 1,
CLI contracts, exceptions, ownership, and persistence behavior. Compatible fixes
use patch releases, compatible additions use minor releases, and breaking public
changes require a major release. Deprecations retain compatibility during 1.x.

External beta participation and a release-candidate cycle are optional. Maintainer
verification is the acceptance mechanism. This record does not claim external
feedback, v1.0.0 publication, or final CI has occurred.

## Existing verification and completed v0.9.0 release

The [completed v0.9.0 record](release-verification-v0.9.0.md) verifies the prior
release and replaces the unfilled publication handoff with observed results.
The [API review](api-review.md), [pipeline matrix](pipeline-coverage.md),
[failure matrix](failure-matrix.md), [packaging review](packaging-verification.md),
and [documentation review](documentation-review.md) remain supporting evidence.

All five jobs passed on the released v0.9.0 commit
`d052986b3363bdb0d3b83d8f482d8a09b4a815e2`:

| Supported combination | Existing release evidence |
| --- | --- |
| Ubuntu / CPython 3.12 | [Full suite, quality, docs, packaging, installed artifacts](https://github.com/apaquette/ETLRelay/actions/runs/39649726342/job/119394567425) |
| Ubuntu / CPython 3.13 | [Both-artifact smoke](https://github.com/apaquette/ETLRelay/actions/runs/39649726342/job/119395168242) |
| Ubuntu / CPython 3.14 | [Both-artifact smoke](https://github.com/apaquette/ETLRelay/actions/runs/39649726342/job/119395168033) |
| macOS / CPython 3.12 | [Both-artifact smoke](https://github.com/apaquette/ETLRelay/actions/runs/39649726342/job/119395168014) |
| Windows / CPython 3.12 | [Both-artifact smoke](https://github.com/apaquette/ETLRelay/actions/runs/39649726342/job/119395168218) |

Support remains these five combinations, rather than all Python/OS pairings.
SQLite is the tested SQL backend; other SQLAlchemy dialects require drivers and
independent verification. Prior results do not satisfy the final v1.0.0 CI gate.

## Local v1.0.0 checks

Local checks passed on Linux with locked dependencies:

- CPython 3.12.14: **736 tests passed, 100% configured statement/branch coverage**,
  including installed-package examples and the actual quick-start snippets.
- Ruff lint/format, Pyright, strict MkDocs, lockfile and installed dependency
  consistency, and diff checks passed.
- Fresh v1.0.0 wheel/sdist builds passed Twine and archive metadata/content checks.
- Both artifacts installed and passed isolated public-import, direct
  CSV/Parquet/SQLite, and CLI/YAML smoke tests on CPython **3.12.14, 3.13.16,
  and 3.14.8**.
- The audit exited successfully with **no known vulnerabilities** and reported
  archived `verspec` (documentation tooling through `mike`). That maintenance
  status remains recorded as later tooling work; no ignore rule or dependency
  change is introduced in this release.
- Diff/lockfile review confirms runtime source, tests, workflows, third-party
  package records, and dependency bounds are unchanged.

Commands are maintained in `RELEASE_CHECKS.md` and the existing
[packaging procedure](packaging-verification.md). These results verify 1.0.0
artifacts independently of an editable install. Local Linux checks do not
replace final macOS/Windows or complete integrated CI for the release commit.

## Final release gates

Follow the [existing release procedure](release-automation.md) and complete the
active `RELEASE_CHECKS.md`:

1. Integrate the v1.0.0 preparation change into `dev`, record its commit/run, and
   require all five CI jobs to pass. Resolve any new release-blocking defect.
2. Run the existing TestPyPI workflow on that reviewed source. Verify installed
   v1.0.0 behavior and do not overwrite any already-published artifact.
3. Promote `dev` to `main`. The production workflow verifies/builds, publishes
   PyPI artifacts, creates the matching GitHub release/tag with the finalized
   notes, and deploys versioned documentation.
4. Verify package metadata, published wheel/sdist, GitHub release/tag, hosted
   `/ETLRelay/1.0.0/` documentation, and pinned `v1.0.0` example/policy links.
5. Record the observed results and close #142 when its release criteria are met.

The changelog and [release notes](release-notes-v1.0.0.md) use the target date;
update both if publication occurs on a different day. Do not describe pending
remote checks or publication as complete based on a local build.

## Limitations and later work

The [scope policy](v1-scope.md) and [security guidance](../security.md) retain
non-atomic/partial file output, append-only per-batch SQL commits, materialized
SQL reads, explicit resource ownership, filesystem race/security limitations,
and the boundary of controlled diagnostic redaction. These are supported,
documented operational constraints and are not unimplemented release features.

Remote storage, more formats/processors/integrations, conversion frameworks,
scheduling/retries, concurrency/distribution, dynamic plugins, and additional
SQL modes remain deferred. The post-v1.0 roadmap will separately evaluate
concrete user workflows, adoption benefits, architectural fit, and maintenance
cost, including whether an idea belongs in the core, an optional integration,
a companion project, or an existing external tool. No such feature is required
for this release.
