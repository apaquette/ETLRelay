# Changelog

Notable changes to ETLRelay are documented here.

This project follows the principles of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [Unreleased]

Changes intended for the first public release are listed below. When preparing the release, move this content to a `0.1.0` section and add the actual release date.

### Added

- Batch-oriented pipeline contracts for sources, processors, and sinks.
- Synchronous pipeline execution with processors applied in sequence.
- An Arrow-backed `Batch` representation.
- Local filesystem access through a stream-based `FileSystem` protocol and `LocalFileSystem` implementation.
- CSV reading and writing through separate reader and writer components.
- `FileSource` and `FileSink` composition of storage and format components.
- Path containment validation for local filesystem paths.
- Unit, integration, and functional tests for the initial local CSV pipeline.

### Notes

- This is an experimental pre-1.0 release. Public APIs may change between minor releases.
- The initial implementation focuses on local filesystem and CSV workflows. SQL, declarative YAML, CLI, Parquet, S3/HDFS, and generic API integrations are not part of this release unless separately implemented and tested.
