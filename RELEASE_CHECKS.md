# v1.0.0 Release Verification

Ticket: #142. Target release date: **2026-10-21**; update the changelog and release
notes if publication moves. Review: `docs/development/release-v1.0.0.md`.
Completed v0.9.0 evidence: `docs/development/release-verification-v0.9.0.md`.

Checked items describe observed preparation/verification. Pending integrated CI,
TestPyPI, and production publication remain unchecked until they actually pass.

## Stable contract and metadata

- [x] The released v0.9.0 feature set is retained without additional runtime API changes.
- [x] Public Python, YAML, CLI, data, exception, resource, and persistence contracts are covered by the compatibility policy.
- [x] Patch/minor/major versioning and deprecation/migration rules are documented.
- [x] External beta feedback and a release-candidate cycle are optional.
- [x] v0.9.0 integrated CI/publication evidence is recorded; #139 and #37 are closed.
- [x] Public issue review found only #142 open and no separate product defect.
- [x] Metadata and lockfile identify `1.0.0`; Python range remains `>=3.12,<3.15`.
- [x] Runtime dependency bounds and third-party locked versions are unchanged.
- [x] README, installation/CLI examples, homepage, security policy, roadmap, changelog, and release notes target v1.0.0.
- [x] Current release-content links use `v1.0.0` / `1.0.0`; historical evidence retains its original release/run.
- [x] No Python/YAML migration is required from v0.9.0; earlier migration notes remain available.
- [x] Known limitations and deferred features are explicit; post-v1.0 work is outside this ticket.

## Local verification

Linux / CPython 3.12.14: **736 tests passed, 100% configured statement/branch
coverage**. Ruff, Pyright, strict MkDocs, dependency consistency, Twine, and
archive-content checks passed. Both v1.0.0 artifacts installed and executed
outside the checkout on CPython **3.12.14, 3.13.16, and 3.14.8**.

The dependency audit exited successfully with no known vulnerabilities. It also
reported archived `verspec`, a transitive documentation dependency of `mike`.
This remains later tooling-maintenance work recorded during v0.9.0; it is not a
runtime dependency or a reported vulnerability. No ignore rule is introduced.

- [x] `uv lock --check` and `uv pip check --python .venv/bin/python` pass.
- [x] `uv audit --locked --preview-features audit-command` reports no known vulnerabilities; assess any adverse status separately.
- [x] Full pytest suite with configured statement/branch coverage passes, including installed examples and the actual quick start.
- [x] Ruff lint/format, Pyright, strict MkDocs, and `git diff --check` pass.
- [x] Fresh wheel/sdist builds pass Twine and `tests/packaging/check_distributions.py`.
- [x] Both v1.0.0 artifacts install and pass `tests/packaging/smoke_compatibility.py dist` outside the checkout on the local supported Python versions.
- [x] Diff review confirms runtime source, tests, workflows, and third-party locked versions remain unchanged.

## Final integrated CI

Release commit and successful CI run: **record after integration**.
Existing v0.9.0 results are supporting evidence, not a replacement for these gates.

- [ ] Ubuntu / CPython 3.12: full suite, quality, docs, packaging, both-artifact smoke.
- [ ] Ubuntu / CPython 3.13: both-artifact smoke.
- [ ] Ubuntu / CPython 3.14: both-artifact smoke.
- [ ] macOS / CPython 3.12: both-artifact smoke.
- [ ] Windows / CPython 3.12: both-artifact smoke.
- [ ] Recheck new issues and resolve any release-blocking defect before promotion.

## Publication

- [ ] Existing TestPyPI workflow publishes and smoke-tests v1.0.0 from reviewed `dev`.
- [ ] Promote the verified source to `main` and production verification/build succeeds.
- [ ] PyPI contains both `etlrelay==1.0.0` artifacts with correct metadata.
- [ ] GitHub release/tag `v1.0.0` targets the released source and uses the finalized notes.
- [ ] Hosted `/ETLRelay/1.0.0/` documentation and pinned example/policy links resolve.
- [ ] Published artifacts, release date/text, and documentation agree; record workflow links/results.
- [ ] Close #142 after publication verification; record any subsequent defects separately.
