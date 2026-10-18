"""Explicit composition of ETLRelay's default configuration components.

This module assembles the default file formats, storage implementations,
source and sink factories, processor factories, component registries, and
configuration validators into a shared component catalog.
"""

from dataclasses import dataclass

from etlrelay.config.processors.dispatcher import ProcessorConfigValidator
from etlrelay.config.processors.filter_rows import (
    FilterRowsConfigFactory,
    FilterRowsConfigValidator,
)
from etlrelay.config.processors.rename_columns import (
    RenameColumnsConfigFactory,
    RenameColumnsConfigValidator,
)
from etlrelay.config.processors.select_columns import (
    SelectColumnsConfigFactory,
    SelectColumnsConfigValidator,
)
from etlrelay.config.processors.sequence import ProcessorSequenceConfigValidator
from etlrelay.config.registry import ComponentRegistration, ComponentRegistry
from etlrelay.config.sinks.dispatcher import SinkConfigValidator
from etlrelay.config.sinks.file import FileSinkConfigFactory, FileSinkConfigValidator
from etlrelay.config.sinks.sql import SqlSinkConfigFactory, SqlSinkConfigValidator
from etlrelay.config.sources.dispatcher import SourceConfigValidator
from etlrelay.config.sources.file import (
    FileSourceConfigFactory,
    FileSourceConfigValidator,
)
from etlrelay.config.sources.sql import SqlSourceConfigFactory, SqlSourceConfigValidator
from etlrelay.config.sql_engine_factory import SqlEngineFactory
from etlrelay.config.storage.dispatcher import StorageConfigValidator
from etlrelay.config.storage.local import (
    LocalFileSystemConfigFactory,
    LocalFileSystemConfigValidator,
)
from etlrelay.config.validator import ConfigValidator
from etlrelay.core import Processor, Reader, Sink, Source, Writer
from etlrelay.file_formats import TabularFileFormatRegistry
from etlrelay.readers import CsvReader, ParquetReader
from etlrelay.storage.filesystem import FileSystem
from etlrelay.writers import CsvWriter, ParquetWriter


@dataclass(frozen=True)
class ComponentCatalog:
    """Bundle shared registries and services for configuration processing.

    The catalog exposes the registries used to resolve storage, source, sink,
    and processor types, as well as the tabular file-format registry, SQL
    engine factory, and root configuration validator.

    File sources and sinks share the catalog's storage and file-format
    registries. SQL sources and sinks share its SQL engine factory.

    Attributes:
        tabular_file_format_registry: Registry of supported tabular readers
            and writers.
        storage_registry: Registry of storage component registrations.
        source_registry: Registry of source component registrations.
        sink_registry: Registry of sink component registrations.
        processor_registry: Registry of processor component registrations.
        sql_engine_factory: Shared provider for preflighted SQL connection
            references and the lifecycle of created SQL engines.
        config_validator: Validator for the root pipeline configuration and
            its component sections.
    """

    tabular_file_format_registry: TabularFileFormatRegistry
    storage_registry: ComponentRegistry[FileSystem]
    source_registry: ComponentRegistry[Source]
    sink_registry: ComponentRegistry[Sink]
    processor_registry: ComponentRegistry[Processor]
    sql_engine_factory: SqlEngineFactory
    config_validator: ConfigValidator


def create_default_component_catalog(
    *,
    sql_engine_factory: SqlEngineFactory | None = None,
) -> ComponentCatalog:
    """Create the default component catalog and its shared dependencies.

    The catalog registers CSV and Parquet readers and writers, local
    filesystem storage, file and SQL sources and sinks, and the
    ``select_columns``, ``rename_columns``, and ``filter_rows`` processors.
    It also assembles the dispatchers and root configuration validator.

    A single set of registries is shared between the corresponding validators
    and factories, and the same SQL engine factory is supplied to both SQL
    component factories.

    Args:
        sql_engine_factory: Optional SQL engine factory to share with the
            catalog's SQL source and sink factories. If omitted, a new
            ``SqlEngineFactory`` is created.

    Returns:
        A ``ComponentCatalog`` containing the default component registries,
        shared SQL engine factory, and root configuration validator.

    Note:
        Creating the catalog assembles configuration components and their
        registrations; it does not invoke component ``build`` methods,
        resolve SQL environment variables, create database engines, open
        files, or execute a pipeline.

        The tabular file-format registry is separate from key-value document
        readers such as ``YamlReader``, which are not registered as tabular
        data formats.
    """
    if sql_engine_factory is None:
        sql_engine_factory = SqlEngineFactory()

    # Tabular serialization formats are distinct from key-value document
    # readers such as YamlReader, which are not part of this registry.
    tabular_file_format_registry: TabularFileFormatRegistry[Reader, Writer] = (
        TabularFileFormatRegistry(
            readers={
                "csv": CsvReader,
                "parquet": ParquetReader,
            },
            writers={
                "csv": CsvWriter,
                "parquet": ParquetWriter,
            },
        )
    )

    # Storage must exist before file component validators and factories.
    storage_registry: ComponentRegistry[FileSystem] = ComponentRegistry(
        {
            "local": ComponentRegistration[FileSystem](
                validator=LocalFileSystemConfigValidator(),
                factory=LocalFileSystemConfigFactory(),
            ),
        }
    )
    storage_validator = StorageConfigValidator(storage_registry)

    # Source and sink validators and factories share the same storage and
    # tabular-format registries.
    source_registry: ComponentRegistry[Source] = ComponentRegistry(
        {
            "file": ComponentRegistration[Source](
                validator=FileSourceConfigValidator(
                    tabular_file_format_registry,
                    storage_validator,
                ),
                factory=FileSourceConfigFactory(
                    storage_registry=storage_registry,
                    format_registry=tabular_file_format_registry,
                ),
            ),
            "sql": ComponentRegistration[Source](
                validator=SqlSourceConfigValidator(),
                factory=SqlSourceConfigFactory(
                    engine_factory=sql_engine_factory,
                ),
            ),
        }
    )

    sink_registry: ComponentRegistry[Sink] = ComponentRegistry(
        {
            "file": ComponentRegistration[Sink](
                validator=FileSinkConfigValidator(
                    tabular_file_format_registry,
                    storage_validator,
                ),
                factory=FileSinkConfigFactory(
                    storage_registry=storage_registry,
                    format_registry=tabular_file_format_registry,
                ),
            ),
            "sql": ComponentRegistration[Sink](
                validator=SqlSinkConfigValidator(),
                factory=SqlSinkConfigFactory(
                    engine_factory=sql_engine_factory,
                ),
            ),
        }
    )

    # Each processor registration pairs its component-specific validator
    # with its class-based factory.
    processor_registry: ComponentRegistry[Processor] = ComponentRegistry(
        {
            "select_columns": ComponentRegistration[Processor](
                validator=SelectColumnsConfigValidator(),
                factory=SelectColumnsConfigFactory(),
            ),
            "rename_columns": ComponentRegistration[Processor](
                validator=RenameColumnsConfigValidator(),
                factory=RenameColumnsConfigFactory(),
            ),
            "filter_rows": ComponentRegistration[Processor](
                validator=FilterRowsConfigValidator(),
                factory=FilterRowsConfigFactory(),
            ),
        }
    )

    # Dispatchers use the same registries exposed by the catalog.
    source_validator = SourceConfigValidator(source_registry)
    sink_validator = SinkConfigValidator(sink_registry)
    processor_validator = ProcessorConfigValidator(processor_registry)
    processor_sequence_validator = ProcessorSequenceConfigValidator(processor_validator)

    config_validator = ConfigValidator(
        source_validator=source_validator,
        sink_validator=sink_validator,
        processor_validator=processor_sequence_validator,
    )

    return ComponentCatalog(
        tabular_file_format_registry=tabular_file_format_registry,
        storage_registry=storage_registry,
        source_registry=source_registry,
        sink_registry=sink_registry,
        processor_registry=processor_registry,
        sql_engine_factory=sql_engine_factory,
        config_validator=config_validator,
    )
