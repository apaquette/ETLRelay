import pytest

from etlrelay.config.storage import LocalFileSystemValidator
from etlrelay.config.validator import ComponentConfigValidator


def test_satisfies_protocol() -> None:
    validator = LocalFileSystemValidator()

    assert isinstance(validator, ComponentConfigValidator)


def test_accepts_local_storage_without_base_path() -> None:
    validator = LocalFileSystemValidator()

    assert validator.validate({"type": "local"}, "source.storage") == []


def test_accepts_local_storage_with_non_empty_base_path() -> None:
    validator = LocalFileSystemValidator()

    assert not validator.validate(
        {"type": "local", "base_path": "./data"},
        "source.storage",
    )


def test_rejects_non_mapping_storage() -> None:
    errors = LocalFileSystemValidator().validate([], "source.storage")

    assert any("source.storage.type" and "mapping" in str(error) for error in errors)


def test_rejects_missing_storage_type() -> None:
    errors = LocalFileSystemValidator().validate({}, "source.storage")

    assert any("source.storage" in str(error) for error in errors)


def test_rejects_non_local_storage_type() -> None:
    errors = LocalFileSystemValidator().validate(
        {"type": "unknown"},
        "source.storage",
    )

    assert any("source.storage.type" in str(error) for error in errors)
    assert any("local" in str(error) for error in errors)


def test_rejects_unknown_local_storage_properties() -> None:
    errors = LocalFileSystemValidator().validate(
        {"type": "local", "region": "ca-central-1"},
        "source.storage",
    )

    assert any("source.storage" and "region" in str(error) for error in errors)
    assert any("region" in str(error) for error in errors)


@pytest.mark.parametrize("value", [None, "", 7, True])
def test_base_path_must_be_a_non_empty_string(value: object) -> None:
    errors = LocalFileSystemValidator().validate(
        {"type": "local", "base_path": value},
        "source.storage",
    )

    assert any("source.storage.base_path" in str(error) for error in errors)


def test_rejects_non_string_property_keys() -> None:
    config: dict[object, object] = {"type": "local", 1: "unexpected"}

    errors = LocalFileSystemValidator().validate(config, "source.storage")

    assert errors
    assert all(isinstance(error, str) for error in errors)
