# Security

ETLRelay 0.6.0 adds versioned YAML configuration, component validation, SQL environment-variable preflight, and a shared SQL engine factory for configuration-built pipelines. These features reduce ambiguity and prevent several classes of configuration error before data operations begin, but they do not form a full security boundary. ETLRelay remains pre-1.0 software; evaluate it in a controlled environment before using it for sensitive or production workloads.

## Local filesystem paths

`PathValidator` resolves candidate paths and verifies that resolved locations remain within the configured base directory. It checks path containment, not existence; the filesystem operation determines whether a read or write succeeds. Parent directories are not created automatically by the local filesystem implementation.

Path validation is not an operating-system sandbox and does not eliminate time-of-check/time-of-use races if another process can modify the filesystem concurrently. Run ETLRelay with only the filesystem permissions it needs and use a dedicated working directory where appropriate.

## YAML configuration safety

`YamlReader` uses a safe YAML loader. It rejects duplicate mapping keys, malformed documents, multiple documents where a single document is expected, non-mapping roots, and non-string root keys. It does not construct arbitrary Python objects from YAML tags.

`ConfigValidator` rejects unknown top-level fields, unknown component properties, unsupported component types, and unsupported schema versions. `PipelineBuilder` resolves explicit registrations; the v0.6.0 configuration format does not support arbitrary imports, `eval`, or unrestricted Python expression execution.

Configuration validation is not a guarantee that runtime inputs are trustworthy. SQL query text is still caller-authored SQL, and data-dependent column/schema constraints can fail during execution.

## SQL connection secrets

Use `connection_url_env` to name an environment variable containing a SQLAlchemy connection URL. Do not put credential-bearing connection URLs, passwords, API tokens, or other secrets directly in YAML files, examples, changelog entries, or version control.

During `PipelineBuilder.build()`, required connection-variable references are preflighted before ETL component factories run. Missing or empty values cause a `PipelineBuildError` before source/sink I/O begins. `SqlEngineFactory` avoids putting resolved connection URLs, credentials, or underlying driver exception text in its own error messages.

Environment variables provide indirection, not a secrets vault. Application deployment remains responsible for setting environment values securely, limiting who can inspect them, preventing them from leaking into logs or diagnostics, and rotating credentials when needed. Avoid logging environment dumps or complete connection URLs. Use a secrets manager or platform-native secret injection appropriate to the deployment when stronger lifecycle and access controls are required.

## SQL safety and limits

Use SQLAlchemy bound parameters for SQL **values**. Do not interpolate untrusted value data into SQL query strings. Bind parameters cannot represent table names, column names, operators, or sort direction; dynamic identifiers require a trusted allowlist and appropriate SQLAlchemy APIs.

`SqlSource` is not a SQL parser, query-policy engine, or authorization boundary. Use database credentials with the minimum required permissions. `SqlSink` appends to an existing table and does not implement a table-creation/migration or replace policy. SQLite is the reference integration-test backend; other SQLAlchemy dialects require suitable drivers and independent verification.

## Resource lifecycle

Direct Python `SqlSource` and `SqlSink` instances borrow the SQLAlchemy engine supplied by the caller; the application owns that engine and disposes it when it is no longer needed.

For YAML-built pipelines, `create_default_component_catalog()` creates or accepts a shared `SqlEngineFactory`, and the `PipelineBuilder` uses it for SQL components. The caller must invoke `builder.close()` after execution to release engines created by this shared factory and discard resolved URLs. Do not close a successful build's engine resources before the pipeline runs.

## Current limitations

ETLRelay does not provide a full filesystem sandbox, credentials vault, SQL authorization layer, external API security model, or remote-storage security model. Remote storage such as S3 and HDFS remains outside the planned v1.0.0 scope. Additional integrations require their own threat review and tests.

For reporting suspected vulnerabilities, follow the procedure in the repository's [Security policy](https://github.com/apaquette/ETLRelay/blob/v0.6.0/SECURITY.md).
