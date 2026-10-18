"""Tests for explicit default ETLRelay component composition."""

from unittest.mock import Mock

from etlrelay.config.processors import (
    FilterRowsConfigFactory,
    FilterRowsConfigValidator,
    RenameColumnsConfigFactory,
    RenameColumnsConfigValidator,
    SelectColumnsConfigFactory,
    SelectColumnsConfigValidator,
)
from etlrelay.config.sinks.file import FileSinkConfigFactory, FileSinkConfigValidator
from etlrelay.config.sinks.sql import SqlSinkConfigFactory, SqlSinkConfigValidator
from etlrelay.config.sources.file import FileSourceConfigFactory, FileSourceConfigValidator
from etlrelay.config.sources.sql import SqlSourceConfigFactory, SqlSourceConfigValidator
from etlrelay.config.sql_engine_factory import SqlEngineFactory
from etlrelay.config.storage.local import (
    LocalFileSystemConfigFactory,
    LocalFileSystemConfigValidator,
)
from etlrelay.default_components import ComponentCatalog, create_default_component_catalog


def valid_file_config() -> dict[str, object]:
    return {
        "version": 1,
        "source": {
            "type": "file",
            "path": "input.csv",
            "format": "csv",
            "storage": {"type": "local"},
        },
        "processors": [],
        "sink": {
            "type": "file",
            "path": "output.csv",
            "format": "csv",
            "storage": {"type": "local"},
        },
    }


def test_create_default_component_catalog_returns_catalog() -> None:
    components = create_default_component_catalog()

    assert isinstance(components, ComponentCatalog)


def test_registers_only_supported_component_types() -> None:
    components = create_default_component_catalog()

    assert components.storage_registry.names() == ("local",)
    assert components.source_registry.names() == ("file", "sql")
    assert components.sink_registry.names() == ("file", "sql")
    assert components.processor_registry.names() == (
        "select_columns",
        "rename_columns",
        "filter_rows",
    )


def test_pairs_each_component_validator_with_its_factory() -> None:
    components = create_default_component_catalog()

    assert isinstance(
        components.storage_registry.get("local").validator,
        LocalFileSystemConfigValidator,
    )
    assert isinstance(
        components.storage_registry.get("local").factory,
        LocalFileSystemConfigFactory,
    )

    assert isinstance(
        components.source_registry.get("file").validator,
        FileSourceConfigValidator,
    )
    assert isinstance(
        components.source_registry.get("file").factory,
        FileSourceConfigFactory,
    )
    assert isinstance(
        components.source_registry.get("sql").validator,
        SqlSourceConfigValidator,
    )
    assert isinstance(
        components.source_registry.get("sql").factory,
        SqlSourceConfigFactory,
    )

    assert isinstance(
        components.sink_registry.get("file").validator,
        FileSinkConfigValidator,
    )
    assert isinstance(
        components.sink_registry.get("file").factory,
        FileSinkConfigFactory,
    )
    assert isinstance(
        components.sink_registry.get("sql").validator,
        SqlSinkConfigValidator,
    )
    assert isinstance(
        components.sink_registry.get("sql").factory,
        SqlSinkConfigFactory,
    )

    assert isinstance(
        components.processor_registry.get("select_columns").validator,
        SelectColumnsConfigValidator,
    )
    assert isinstance(
        components.processor_registry.get("select_columns").factory,
        SelectColumnsConfigFactory,
    )
    assert isinstance(
        components.processor_registry.get("rename_columns").validator,
        RenameColumnsConfigValidator,
    )
    assert isinstance(
        components.processor_registry.get("rename_columns").factory,
        RenameColumnsConfigFactory,
    )
    assert isinstance(
        components.processor_registry.get("filter_rows").validator,
        FilterRowsConfigValidator,
    )
    assert isinstance(
        components.processor_registry.get("filter_rows").factory,
        FilterRowsConfigFactory,
    )


def test_default_formats_are_readable_and_writable() -> None:
    components = create_default_component_catalog()

    assert components.tabular_file_format_registry.readable_formats() == ("csv", "parquet")
    assert components.tabular_file_format_registry.writable_formats() == ("csv", "parquet")


def test_config_validator_uses_the_default_registrations() -> None:
    components = create_default_component_catalog()
    config = valid_file_config()

    components.config_validator.validate(config)

    invalid = valid_file_config()
    invalid["source"] = {"type": "unsupported"}

    try:
        components.config_validator.validate(invalid)
    except Exception as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("Unsupported source type should be rejected")


def test_composition_does_not_resolve_environment_variables_or_create_engines() -> None:
    sql_engine_factory = Mock(spec=SqlEngineFactory)

    components = create_default_component_catalog(
        sql_engine_factory=sql_engine_factory,
    )

    assert components.sql_engine_factory is sql_engine_factory
    sql_engine_factory.create.assert_not_called()
