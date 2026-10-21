# API Reference

This reference documents ETLRelay's public Python interfaces and
implementations using their source-code docstrings.

ETLRelay v0.8.0 retains the existing source, processor, sink, storage,
configuration, and CLI interfaces while strengthening their documented
security and operational contracts.

Important runtime behaviors include:

- Local filesystem path containment and explicit stream ownership.
- Lazy batch processing and deterministic cleanup of closeable pipeline
  iterators.
- Output-schema validation, including zero-row batches.
- SQLAlchemy connection and result cleanup.
- Per-batch SQL transactions and append-only persistence.
- Configuration validation and SQL environment-variable preflight.
- Exception propagation and controlled operational logging.

The Python API generally preserves underlying runtime exceptions.
The CLI provides separate error-reporting and exit-code conventions,
documented in the [CLI Reference](cli-reference.md).

Configuration schema version `1` remains supported and is independent
of the ETLRelay package version.

ETLRelay remains pre-1.0 software. Public interfaces may change before
v1.0.0.

Consult the [YAML Configuration](configuration.md),
[Security](security.md), [Logging](logging.md), and
[Architecture](architecture/overview.md) documentation for detailed
usage contracts and limitations.

## Configuration loading and validation

::: etlrelay.config.loader.ConfigLoader

::: etlrelay.config.validator.ConfigValidator

::: etlrelay.config.errors.ConfigurationError

::: etlrelay.readers.yaml.YamlReader

::: etlrelay.core.reader.KeyValueReader

## Configuration construction

::: etlrelay.default_components.ComponentCatalog

::: etlrelay.default_components.create_default_component_catalog

::: etlrelay.config.registry.ComponentRegistration

::: etlrelay.config.registry.ComponentRegistry

::: etlrelay.config.component_validator.ComponentConfigValidator

::: etlrelay.config.component_dispatcher.ComponentConfigDispatcher

::: etlrelay.config.pipeline_builder.PipelineBuilder

::: etlrelay.config.pipeline_builder.PipelineBuildError

::: etlrelay.config.sql_engine_factory.SqlEngineProvider

::: etlrelay.config.sql_engine_factory.SqlEngineFactory

::: etlrelay.config.sql_engine_factory.SqlEngineFactoryError

## Core contracts and data model

::: etlrelay.core.batch.Batch

::: etlrelay.core.source.Source

::: etlrelay.core.processor.Processor

::: etlrelay.core.sink.Sink

::: etlrelay.core.reader.Reader

::: etlrelay.core.writer.Writer

## Pipeline

::: etlrelay.pipeline.pipeline.Pipeline

## Processors

::: etlrelay.processors.select_columns.SelectColumns

::: etlrelay.processors.rename_columns.RenameColumns

::: etlrelay.processors.filter_rows.FilterRows

## Filesystem and security

::: etlrelay.security.path.PathValidator

::: etlrelay.storage.filesystem.FileSystemError

::: etlrelay.storage.filesystem.FileSystem

::: etlrelay.storage.local.LocalFileSystem

## File source and sink

::: etlrelay.sources.file.FileSource

::: etlrelay.sinks.file.FileSink

## SQL source and sink

::: etlrelay.sources.sql.SqlSource

::: etlrelay.sinks.sql.SqlSink

## CSV reader and writer

::: etlrelay.readers.csv.CsvReader

::: etlrelay.writers.csv.CsvWriter

## Parquet reader and writer

::: etlrelay.readers.parquet.ParquetReader

::: etlrelay.writers.parquet.ParquetWriter
