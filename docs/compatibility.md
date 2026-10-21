# Compatibility and Versioning Policy

This policy applies from ETLRelay v1.0.0. The supported product and environment
matrix are defined in the [scope and support policy](development/v1-scope.md).
The [API reference](api-reference.md), [configuration reference](configuration.md),
and [CLI reference](cli-reference.md) define the behavior covered by this policy.

## Stable public contract

| Surface | Compatibility commitment |
| --- | --- |
| Python API | Documented public import paths, names, constructors, arguments, protocol signatures, return values, and documented exception types/conditions remain compatible within a major release. |
| Data and execution | Documented `Batch` schema/empty-data semantics, processor predicates and null handling, ordering, exception propagation, ownership, cleanup, overwrite behavior, and transaction boundaries remain compatible. |
| YAML schema version 1 | Existing valid configurations keep their meaning and remain usable within ETLRelay 1.x. Schema version and package version are independent. |
| CLI | Documented commands, arguments/options, exit codes, and explicitly specified output contracts remain compatible within a major release. |
| Supported environments | Removing a declared Python/platform combination or tested database from support is a breaking change. New verified combinations may be added compatibly. |

Use the responsibility-level convenience packages documented in the API reference,
such as `etlrelay.core`, `etlrelay.readers`, and `etlrelay.pipeline`. Public classes
and functions explicitly documented through their implementation modules are also
covered, including configuration services and registrations. These import paths
remain supported even if internal organization changes. The root `etlrelay`
package does not provide an umbrella re-export API.

`TabularReader` and `TabularWriter` are the public tabular protocols.
`KeyValueReader` reads a mapping-shaped document and remains separate from row
records. The former `Reader`/`Writer` class names were removed in v0.9.0 and are
not restored by v1.0.0. See the [migration guide](development/migration-v0.9.0.md)
when upgrading from earlier releases. No code or YAML migration is needed from
v0.9.0 to v1.0.0.

## Release rules

ETLRelay follows [Semantic Versioning](https://semver.org/):

- **Patch (`1.0.1`):** Compatible correctness, security, documentation, packaging,
  or maintenance fixes. Correcting behavior to match the documented contract may
  change the outcome of previously invalid or defective usage.
- **Minor (`1.1.0`):** Backward-compatible additions. Existing supported calls,
  configurations, and workflows retain their documented behavior. New optional
  configuration fields may be accepted, but existing schema version 1 settings
  must preserve their meaning.
- **Major (`2.0.0`):** Incompatible changes to the supported contract, including
  removal/renaming of public imports, incompatible argument/return or failure
  semantics, changed persistence guarantees, or rejection/reinterpretation of
  previously valid configuration. A new schema version does not justify breaking
  existing version 1 support within ETLRelay 1.x.

A security fix follows the same compatibility classification. If a required fix
cannot preserve the supported contract, document the impact and migration and
publish an appropriate major release rather than silently weakening this policy.

Published package files and tagged source are not replaced. Corrections use a
new release and updated release notes. Historical documentation stays pinned to
its release; current documentation and repository examples use the target
version rather than moving branches or documentation aliases.

## Deprecation and migration

Introduce public deprecations in a minor release, document the replacement and
migration, and retain the deprecated contract throughout the remainder of that
major line. Use a `DeprecationWarning` for Python APIs where practical. Remove
supported deprecated behavior only in a subsequent major release, after at
least one minor release has carried the notice. No fixed calendar support period
is promised.

Document breaking changes and required migration in the changelog, release notes,
and relevant references. Pre-1.0 migration notes remain historical guidance.

## Boundaries and exclusions

The compatibility promise does not turn every importable object or upstream
behavior into ETLRelay's public API. It excludes:

- Private names and modules (leading `_`), undocumented helpers/attributes,
  internal call order, and internal registry/cache representations.
- Exact wording, formatting, timestamps, ordering, or volume of help text,
  human-readable errors, and operational logs, except output explicitly specified
  as a CLI contract. Use documented exit codes for command failure handling.
- Exact messages/types of arbitrary third-party exceptions where ETLRelay only
  promises propagation; documented ETLRelay exception contracts remain covered.
- Byte-for-byte serialized output, performance thresholds, or external library
  internals beyond ETLRelay's documented data/schema and format behavior.
- Untested database dialects, undeclared Python/platform combinations, unsupported
  usage, and deferred features listed in the scope policy.

Dependency constraints are declared in package metadata and verified in CI.
Dependency upgrades require regression and artifact checks appropriate to their
impact; they do not automatically expand ETLRelay's supported environments or
public functionality. The lockfile records release verification inputs rather
than promising every transitive version will remain fixed throughout 1.x.

The stable contract includes the existing limitations: local writes can truncate
files and leave partial output; SQL output appends to existing tables with one
transaction per nonempty batch; earlier committed output survives later failures.
Path containment is not a sandbox, and controlled diagnostics do not guarantee
sanitization of arbitrary third-party logs. See [Security](security.md).

## Release acceptance

Maintainer verification establishes readiness using the existing test, quality,
artifact, documentation, dependency, and support-matrix checks. External beta
participation, a minimum user count, and an RC cycle are optional. They are not
acceptance requirements for v1.0.0. New features and broader adoption work are
considered through a separate post-v1.0 roadmap.
