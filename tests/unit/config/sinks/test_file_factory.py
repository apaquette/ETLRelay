"""Unit tests for class-based file sink construction."""

from collections.abc import Mapping
from unittest.mock import Mock, patch

from etlrelay.config.sinks.file import FileSinkConfigFactory


def test_build_composes_storage_writer_and_file_sink() -> None:
    config: Mapping[str, object] = {
        "type": "file",
        "path": "data/output.csv",
        "format": "csv",
        "storage": {"type": "local", "base_path": "/data"},
    }
    storage = Mock(name="storage")
    writer = Mock(name="writer")
    storage_factory = Mock(name="storage_factory")
    storage_factory.build.return_value = storage
    storage_registration = Mock(name="storage_registration")
    storage_registration.factory = storage_factory
    storage_registry = Mock(name="storage_registry")
    storage_registry.get.return_value = storage_registration
    format_registry = Mock(name="format_registry")
    format_registry.create_writer.return_value = writer

    with patch("etlrelay.config.sinks.file.FileSink") as sink_constructor:
        result = FileSinkConfigFactory(
            storage_registry=storage_registry,
            format_registry=format_registry,
        ).build(config)

    storage_registry.get.assert_called_once_with("local")
    storage_factory.build.assert_called_once_with(config["storage"])
    format_registry.create_writer.assert_called_once_with("csv")
    sink_constructor.assert_called_once_with(
        path="data/output.csv",
        storage=storage,
        writer=writer,
    )
    assert result is sink_constructor.return_value


def test_build_does_not_mutate_configuration() -> None:
    storage_config = {"type": "local"}
    config: Mapping[str, object] = {
        "type": "file",
        "path": "output.parquet",
        "format": "parquet",
        "storage": storage_config,
    }
    original = {
        "type": "file",
        "path": "output.parquet",
        "format": "parquet",
        "storage": dict(storage_config),
    }
    storage_factory = Mock()
    storage_factory.build.return_value = Mock(name="storage")
    storage_registration = Mock()
    storage_registration.factory = storage_factory
    storage_registry = Mock()
    storage_registry.get.return_value = storage_registration
    format_registry = Mock()
    format_registry.create_writer.return_value = Mock(name="writer")

    with patch("etlrelay.config.sinks.file.FileSink"):
        FileSinkConfigFactory(
            storage_registry=storage_registry,
            format_registry=format_registry,
        ).build(config)

    assert config == original
