# Security

ETLRelay is experimental pre-1.0 software. It should be evaluated in a non-production environment before it is used for important or sensitive workloads.

## Local filesystem paths

`PathValidator` resolves candidate paths and verifies that their resolved locations remain within the configured base directory. It checks path containment; it deliberately does not check existence. The filesystem operation determines whether a read or write succeeds.

This validation is not an operating-system sandbox and does not eliminate time-of-check/time-of-use races if another process can change the filesystem concurrently. Run ETLRelay with only the filesystem permissions it needs and use a dedicated working directory where appropriate.

## Current limitations


## Current limitations

ETLRelay does not provide a complete filesystem sandbox, credentials vault,
SQL security layer, external API security model, or remote-storage security
model. These capabilities must be designed and tested before any
corresponding integrations are introduced.

The v0.4.0 milestone and planned v1.0.0 scope support local filesystem
storage only. S3, HDFS, and other remote-storage backends are explicitly
outside both scopes.

Additional storage or platform integrations may be reviewed after v1.0.0
if concrete requirements justify them. No particular integration or
release date is promised.


For reporting suspected vulnerabilities, follow the procedure in the repository's [Security policy](https://github.com/apaquette/ETLRelay/blob/main/SECURITY.md).
