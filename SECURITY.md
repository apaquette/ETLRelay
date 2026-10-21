# Security Policy

## Supported versions

ETLRelay is experimental pre-1.0 software.

Security reports are assessed against the latest released version, currently **v0.8.0**. Security fixes and backports for older releases are not guaranteed unless maintainers explicitly announce otherwise.

Public APIs and security-related implementation details may change before v1.0.0.

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities in public GitHub issues, pull requests, or discussions.

Use GitHub's private vulnerability reporting feature if it is enabled for this repository (**Security → Report a vulnerability**). If it is unavailable, contact the maintainer through a verified private channel and confirm the disclosure process before transmitting sensitive technical details.

A useful report includes:

- The affected ETLRelay version or commit.
- The affected component or configuration.
- A description of the security impact.
- Reproduction steps using synthetic data and test credentials.
- Any relevant environmental assumptions or prerequisites.

Do not include real credentials, private datasets, production records, or other sensitive information.

Reports will be reviewed as promptly as reasonably possible. No fixed acknowledgement, remediation, or disclosure timeline is guaranteed.

## Security scope

ETLRelay v0.8.0 includes security-related controls for:

- Local filesystem path containment, including resolved path traversal and symlink escapes.
- Safe YAML configuration parsing and strict schema validation.
- Explicit component registration rather than arbitrary configuration-driven code imports.
- SQLAlchemy bound query values and structured SQL statement construction.
- Environment-variable references for SQL connection URLs.
- Validation and SQL connection-reference preflight before configured pipeline execution.
- Controlled operational logging and CLI error reporting.
- Resource cleanup and explicit file and SQL failure semantics.
- Dependency auditing and installed-distribution verification in CI.

These controls address specific risks but do not make ETLRelay a security sandbox, SQL authorization layer, secrets vault, or production-certified processing platform.

ETLRelay can access files, databases, and other resources permitted to the process and its configured dependencies. It is not designed to safely execute arbitrary untrusted SQL, custom Python components, or configuration supplied by mutually untrusted users.

## Deployment responsibilities

Applications using ETLRelay remain responsible for:

- Running the process with appropriate filesystem and database permissions.
- Protecting credentials and connection environment variables.
- Controlling access to configuration files, input data, outputs, and operational logs.
- Securing the surrounding operating system, runtime, and infrastructure.
- Validating application-specific data and SQL authorization requirements.
- Managing backups, recovery, monitoring, and dependency updates.

ETLRelay does not guarantee atomic file replacement, whole-pipeline transactions, automatic retries, or rollback of previously persisted output.

Evaluate ETLRelay in a controlled environment before using it with sensitive or production data.

For implementation details, security boundaries, and current limitations, see the [Security documentation](https://apaquette.github.io/ETLRelay/0.9.0/security/).

## Policy maintenance

The repository maintainer should verify that private vulnerability reporting is configured correctly and that the published reporting instructions remain accessible.

This policy will be reviewed as ETLRelay approaches v1.0.0 and its deployment requirements become clearer.