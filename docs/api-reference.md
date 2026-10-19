# API Reference

This reference documents ETLRelay's Python API using public classes,
interfaces, and their docstrings.

Configuration APIs introduced in ETLRelay 0.6.0 are grouped separately
from the direct runtime component APIs. The command-line interface
introduced in ETLRelay 0.7.0 is documented in the
[CLI Reference](cli-reference.md).

The public API may evolve before the 1.0.0 release. Consult the
configuration and architecture documentation for supported YAML
properties, component combinations, and implementation boundaries.

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
