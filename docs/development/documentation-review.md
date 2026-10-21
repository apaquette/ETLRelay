# v0.9.0 Documentation Review

Ticket: **0.9.0-07 — Complete documentation for the frozen feature set**.
Reviewed baseline: `dev` commit `493008769ae5ca60daf4b2454c35d635e1793c5b`.

## Review and completion evidence

| Area | Documentation and verification |
| --- | --- |
| Installation and quick start | README and `getting-started.md` distinguish published v0.8.0 from the unreleased candidate, document fresh environments, and provide self-contained CSV/YAML/Python code. |
| Python and YAML examples | `examples/README.md` and `examples/configuration/README.md` document inputs, expected outputs, SQL variable setup on POSIX/PowerShell, and reset/append behavior. |
| Public API and architecture | Generated API targets resolve, `ComponentFactory` is included, canonical imports are documented, stale component-module names and release-specific wording are corrected. |
| Configuration and CLI | Schema version 1 remains unchanged. References document required/optional properties, supported types, invalid document errors, exit codes, process-relative paths, and validation versus build preflight. |
| Errors and persistence | Existing API/failure evidence is carried into user references: schema compatibility, empty input/batches, owned/borrowed streams, exception precedence, SQL transactions, and partial/unreadable outputs. |
| Security and logging | Existing security boundaries remain explicit. Logging includes the controlled Parquet finalization warning and does not promise universal third-party redaction. |
| Extension and contribution | Development instructions show direct structural-protocol composition and point to an executable application-defined processor. Default CLI registration remains fixed; arbitrary plugin loading is unsupported. |
| Development and release | Existing MkDocs/CI tools remain canonical. Root release instructions link to the maintained procedure instead of repeating stale setup-bundle instructions. |
| Migration and draft release | `migration-v0.9.0.md`, `release-notes-v0.9.0.md`, and the changelog cover removed protocol names, retained module paths, corrected exceptions/exit codes, and the Polars dependency removal. |
| Limitations and deferred work | The scope policy and release draft retain the local-file/SQLite boundary and explicitly defer remote storage, document writing, record conversion, and execution/orchestration expansion. |

## Executable documentation checks

The existing isolated-wheel fixture in `tests/functional/test_cli_installed.py`
is reused by two focused tests:

- `test_installed_candidate_runs_documented_examples` copies examples outside
  the checkout, executes five Python programs, validates/runs all nine YAML
  files through the installed CLI, and exercises the shared Python runner for
  file and SQL configurations. It resets demo SQL tables between independent
  runs, checks persisted records and schemas, and proves validation leaves
  outputs untouched.
- `test_installed_candidate_runs_quick_start` extracts the actual first CSV,
  YAML, and Python fences from `getting-started.md`, executes them in a fresh
  working directory, and compares both outputs with the documented records.

The candidate wheel and its runtime dependencies are installed in a separate
virtual environment. The fixture checks import isolation; the example processes
use that environment's Python and CLI without checkout imports or editable
installation. Tests compare outputs rather than relying on successful exit alone.

The new custom processor is example/application code, not a built-in component
or a YAML schema addition. The Parquet example now writes to its dedicated
`examples/data/` directory consistently with the other file examples; generated
outputs are ignored by Git.

## Coordination with preceding tickets

- API review: protocol names, import paths, YAML/CLI failure corrections, and
  public exception behavior are reflected in migration and user references.
- Pipeline coverage: the nine supported pairs remain documented; actual example
  files are tested separately from synthetic component-combination fixtures.
- Failure matrix: borrowed ownership, schema failures, transaction boundaries,
  safe diagnostics, and Parquet finalization precedence are preserved.
- Packaging: supported Python versions/platform combinations, both-artifact
  checks, and removal of unused runtime Polars are incorporated. The packaging
  record now confirms all five CI jobs passed for integrated packaging commit
  `4930087` in run `39637775631`. This is separate from the current documentation
  change, which still requires its own CI.

## Local validation

Linux / CPython 3.12.14 with locked dependencies:

- Full suite: **736 passed**, with **100%** configured statement/branch coverage.
- Both new installed-candidate documentation tests: passed.
- Ruff lint and formatting, Pyright, strict MkDocs build, and diff checks: passed.

Documentation acceptance criteria are satisfied locally. Integration and required
CI checks remain necessary. The v0.9.0 beta ticket must assign the release version,
finalize the changelog date and release text, confirm integrated packaging results,
review release blockers, and gather feedback. No package or documentation has
been published by this review.
