"""Unit tests for component configuration validators."""

from unittest.mock import Mock

import pytest

from etlrelay.config.sinks import FileSinkConfigValidator
from etlrelay.config.sources.file import FileSourceConfigValidator
from etlrelay.config.storage import LocalFileSystemConfigValidator
from etlrelay.file_formats import TabularFileFormatRegistry


class StubStorageValidator:
    """Record nested storage validation without validating real storage."""

    def __init__(self, errors: list[str] | None = None) -> None:
        self.errors = errors if errors is not None else []
        self.calls: list[tuple[object, str]] = []

    def validate(self, config: object, path: str) -> list[str]:
        self.calls.append((config, path))
        return self.errors


def make_format_registry(
    readable: tuple[str, ...] = ("csv", "parquet"),
    writable: tuple[str, ...] = ("csv", "parquet"),
) -> TabularFileFormatRegistry[object, object]:
    """Create a registry with independent read and write capabilities."""
    return TabularFileFormatRegistry(
        readers={name: Mock() for name in readable},
        writers={name: Mock() for name in writable},
    )


def valid_file_config() -> dict[str, object]:
    """Return a valid file component configuration."""
    return {
        "type": "file",
        "path": "data.csv",
        "format": "csv",
        "storage": {"type": "local"},
    }


def test_local_storage_accepts_default_base_path() -> None:
    validator = LocalFileSystemConfigValidator()

    assert validator.validate({"type": "local"}, "source.storage") == []


def test_local_storage_accepts_explicit_base_path() -> None:
    validator = LocalFileSystemConfigValidator()

    assert (
        validator.validate(
            {"type": "local", "base_path": "/data"},
            "source.storage",
        )
        == []
    )


@pytest.mark.parametrize("config", [None, [], "local", 42])
def test_local_storage_rejects_non_mapping_config(config: object) -> None:
    validator = LocalFileSystemConfigValidator()

    errors = validator.validate(config, "source.storage")

    assert any("mapping" in error for error in errors)


def test_local_storage_rejects_wrong_type() -> None:
    validator = LocalFileSystemConfigValidator()

    errors = validator.validate(
        {"type": "remote"},
        "source.storage",
    )

    assert any("source.storage.type" in error for error in errors)


@pytest.mark.parametrize("base_path", ["", "   ", 42, None])
def test_local_storage_rejects_invalid_base_path(
    base_path: object,
) -> None:
    validator = LocalFileSystemConfigValidator()

    errors = validator.validate(
        {"type": "local", "base_path": base_path},
        "source.storage",
    )

    assert any("source.storage.base_path" in error for error in errors)


def test_local_storage_rejects_unknown_fields() -> None:
    validator = LocalFileSystemConfigValidator()

    errors = validator.validate(
        {"type": "local", "directory": "/data"},
        "source.storage",
    )

    assert any("directory" in error for error in errors)


def test_file_source_accepts_readable_format() -> None:
    storage_validator = StubStorageValidator()
    validator = FileSourceConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=storage_validator,
    )

    errors = validator.validate(valid_file_config(), "source")

    assert errors == []
    assert storage_validator.calls == [({"type": "local"}, "source.storage")]


def test_file_source_requires_its_fields() -> None:
    validator = FileSourceConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=StubStorageValidator(),
    )

    errors = validator.validate({}, "source")

    for field in ("type", "path", "format", "storage"):
        assert any(f"source.{field}" in error for error in errors)


@pytest.mark.parametrize("path", ["", "   ", 42, None])
def test_file_source_rejects_invalid_path(path: object) -> None:
    config = valid_file_config()
    config["path"] = path
    validator = FileSourceConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=StubStorageValidator(),
    )

    errors = validator.validate(config, "source")

    assert any("source.path" in error for error in errors)


def test_file_source_rejects_format_without_reader() -> None:
    validator = FileSourceConfigValidator(
        format_registry=make_format_registry(
            readable=("csv",),
            writable=("parquet",),
        ),
        storage_validator=StubStorageValidator(),
    )
    config = valid_file_config()
    config["format"] = "parquet"

    errors = validator.validate(config, "source")

    assert any("source.format" in error for error in errors)


def test_file_source_rejects_wrong_component_type() -> None:
    validator = FileSourceConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=StubStorageValidator(),
    )
    config = valid_file_config()
    config["type"] = "sql"

    errors = validator.validate(config, "source")

    assert any("source.type" in error for error in errors)


def test_file_source_rejects_unknown_fields() -> None:
    validator = FileSourceConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=StubStorageValidator(),
    )
    config = valid_file_config()
    config["encoding"] = "utf-8"

    errors = validator.validate(config, "source")

    assert any("encoding" in error for error in errors)


def test_file_source_propagates_storage_validation_errors() -> None:
    storage_validator = StubStorageValidator(["source.storage: invalid storage configuration"])
    validator = FileSourceConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=storage_validator,
    )

    errors = validator.validate(valid_file_config(), "source")

    assert errors == ["source.storage: invalid storage configuration"]


def test_file_source_rejects_non_mapping_config() -> None:
    validator = FileSourceConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=StubStorageValidator(),
    )

    errors = validator.validate(None, "source")

    assert any("mapping" in error for error in errors)


def test_file_sink_accepts_writable_format() -> None:
    validator = FileSinkConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=StubStorageValidator(),
    )

    assert validator.validate(valid_file_config(), "sink") == []


def test_file_sink_rejects_format_without_writer() -> None:
    validator = FileSinkConfigValidator(
        format_registry=make_format_registry(
            readable=("csv",),
            writable=("parquet",),
        ),
        storage_validator=StubStorageValidator(),
    )
    config = valid_file_config()
    config["format"] = "csv"

    errors = validator.validate(config, "sink")

    assert any("sink.format" in error for error in errors)


def test_file_sink_rejects_wrong_component_type() -> None:
    validator = FileSinkConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=StubStorageValidator(),
    )
    config = valid_file_config()
    config["type"] = "sql"

    errors = validator.validate(config, "sink")

    assert any("sink.type" in error for error in errors)


def test_file_sink_rejects_unknown_fields() -> None:
    validator = FileSinkConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=StubStorageValidator(),
    )
    config = valid_file_config()
    config["unexpected"] = True

    errors = validator.validate(config, "sink")

    assert any("unexpected" in error for error in errors)


@pytest.mark.parametrize("format_name", ["", "   ", 42, None])
def test_file_source_rejects_invalid_format(
    format_name: object,
) -> None:
    config = valid_file_config()
    config["format"] = format_name

    validator = FileSourceConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=StubStorageValidator(),
    )

    errors = validator.validate(config, "source")

    assert any("source.format" in error for error in errors)


def test_file_sink_rejects_non_mapping_config() -> None:
    validator = FileSinkConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=StubStorageValidator(),
    )

    errors = validator.validate(None, "sink")

    assert any("mapping" in error for error in errors)


def test_file_sink_requires_its_fields() -> None:
    validator = FileSinkConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=StubStorageValidator(),
    )

    errors = validator.validate({}, "sink")

    for field in ("type", "path", "format", "storage"):
        assert any(f"sink.{field}" in error for error in errors)


@pytest.mark.parametrize("path", ["", "   ", 42, None])
def test_file_sink_rejects_invalid_path(path: object) -> None:
    config = valid_file_config()
    config["path"] = path

    validator = FileSinkConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=StubStorageValidator(),
    )

    errors = validator.validate(config, "sink")

    assert any("sink.path" in error for error in errors)


@pytest.mark.parametrize("format_name", ["", "   ", 42, None])
def test_file_sink_rejects_invalid_format(
    format_name: object,
) -> None:
    config = valid_file_config()
    config["format"] = format_name

    validator = FileSinkConfigValidator(
        format_registry=make_format_registry(),
        storage_validator=StubStorageValidator(),
    )

    errors = validator.validate(config, "sink")

    assert any("sink.format" in error for error in errors)
