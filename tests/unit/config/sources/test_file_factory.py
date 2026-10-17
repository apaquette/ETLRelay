"""Unit tests for class-based file source construction."""

from collections.abc import Mapping
from unittest.mock import Mock, patch

from etlrelay.config.sources.file import FileSourceConfigFactory


class StubValidator:
    """Minimal validator satisfying ComponentConfigValidator."""

    def validate(self, config: object, path: str) -> list[str]:
        return []


def test_build_composes_storage_reader_and_file_source() -> None:
    config: Mapping[str, object] = {
        "type": "file",
        "path": "data/input.parquet",
        "format": "parquet",
        "storage": {"type": "local", "base_path": "/data"},
    }
    storage = Mock(name="storage")
    reader = Mock(name="reader")
    storage_factory = Mock(name="storage_factory")
    storage_factory.build.return_value = storage
    storage_registration = Mock(name="storage_registration")
    storage_registration.factory = storage_factory
    storage_registry = Mock(name="storage_registry")
    storage_registry.get.return_value = storage_registration
    format_registry = Mock(name="format_registry")
    format_registry.create_reader.return_value = reader

    with patch("etlrelay.config.sources.file.FileSource") as source_constructor:
        result = FileSourceConfigFactory(
            storage_registry=storage_registry,
            format_registry=format_registry,
        ).build(config)

    storage_registry.get.assert_called_once_with("local")
    storage_factory.build.assert_called_once_with(config["storage"])
    format_registry.create_reader.assert_called_once_with("parquet")
    source_constructor.assert_called_once_with(
        path="data/input.parquet",
        storage=storage,
        reader=reader,
    )
    assert result is source_constructor.return_value


def test_build_does_not_mutate_configuration() -> None:
    storage_config = {"type": "local", "base_path": "/data"}
    config: Mapping[str, object] = {
        "type": "file",
        "path": "input.csv",
        "format": "csv",
        "storage": storage_config,
    }
    original = {
        "type": "file",
        "path": "input.csv",
        "format": "csv",
        "storage": dict(storage_config),
    }
    storage_factory = Mock()
    storage_factory.build.return_value = Mock(name="storage")
    storage_registration = Mock()
    storage_registration.factory = storage_factory
    storage_registry = Mock()
    storage_registry.get.return_value = storage_registration
    format_registry = Mock()
    format_registry.create_reader.return_value = Mock(name="reader")

    with patch("etlrelay.config.sources.file.FileSource"):
        FileSourceConfigFactory(
            storage_registry=storage_registry,
            format_registry=format_registry,
        ).build(config)

    assert config == original
