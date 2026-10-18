"""Explicit composition of ETLRelay's default configuration components."""

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
    """Shared registries and services used for validation and construction."""

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
    """Create the default validators, factories, and component registries.

    Construction is lazy with respect to runtime components: this function
    creates registrations but does not call their component factories,
    resolve SQL environment variables, create database engines, open files,
    or execute a pipeline.
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
