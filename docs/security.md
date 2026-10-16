# Security

ETLRelay is experimental pre-1.0 software. It should be evaluated in a non-production environment before it is used for important or sensitive workloads.

## Local filesystem paths

`PathValidator` resolves candidate paths and verifies that their resolved locations remain within the configured base directory. It checks path containment; it deliberately does not check existence. The filesystem operation determines whether a read or write succeeds.

This validation is not an operating-system sandbox and does not eliminate time-of-check/time-of-use races if another process can change the filesystem concurrently. Run ETLRelay with only the filesystem permissions it needs and use a dedicated working directory where appropriate.

## Current limitations


## Current limitations

ETLRelay does not provide a complete filesystem sandbox, credentials vault, SQL authorization/query-policy layer, external API security model, or remote-storage security model. SQL query values can be bound through `SqlSource`, and `SqlSink` delegates destination-table statement construction to SQLAlchemy; these mechanisms do not make caller-authored SQL text or uncontrolled identifiers safe. The application remains responsible for query structure, database permissions, and secret handling.

## SQL values and identifiers

`SqlSource` supports SQLAlchemy bound parameters for query values. Use named placeholders (for example, `:customer_id`) and pass the value separately through `parameters`; do not interpolate untrusted values into SQL text. This is a narrow parameterization facility, not a complete SQL authorization or query-policy layer.

SQL identifiers such as table and column names cannot be supplied as ordinary bind parameters. `SqlSink` passes the configured destination table and optional schema to SQLAlchemy table-reflection/insert APIs, which handle dialect-aware identifier quoting. If an application constructs dynamic source query text, it must keep the query structure trusted and validate/allowlist dynamic identifiers. Never treat caller-controlled SQL text as safe merely because query values are bound.

The application is responsible for creating a least-privilege database engine/connection, protecting any credentials in real connection URLs, and following its database's authorization rules. Documentation examples use in-memory SQLite and contain no credentials.


The file-storage implementation supports the local filesystem only. S3, HDFS, and other remote-storage backends remain outside the planned v1.0.0 scope. SQL sources and sinks are separate SQLAlchemy-backed components; SQLite is the repeatable integration-test backend, while other database dialects need their matching driver and independent verification.

Additional storage or platform integrations may be reviewed after v1.0.0
if concrete requirements justify them. No particular integration or
release date is promised.


For reporting suspected vulnerabilities, follow the procedure in the repository's [Security policy](https://github.com/apaquette/ETLRelay/blob/main/SECURITY.md).
