from unittest.mock import create_autospec

from etlrelay.config.storage import StorageConfigValidator
from etlrelay.config.validator import ComponentConfigValidator


def test_dispatches_to_matching_storage_validator() -> None:
    local_validator = create_autospec(
        ComponentConfigValidator,
        instance=True,
    )
    local_validator.validate.return_value = []

    validator = StorageConfigValidator(validators={"local": local_validator})
    config = {"type": "local", "base_path": "./data"}

    errors = validator.validate(config, "source.storage")

    assert errors == []
    local_validator.validate.assert_called_once_with(
        config,
        "source.storage",
    )


def test_rejects_non_mapping_storage() -> None:
    validator = StorageConfigValidator(validators={})

    errors = validator.validate([], "source.storage")

    assert any("source.storage" in error and "mapping" in error for error in errors)


def test_requires_storage_type() -> None:
    validator = StorageConfigValidator(
        validators={
            "local": create_autospec(
                ComponentConfigValidator,
                instance=True,
            )
        }
    )

    errors = validator.validate({}, "source.storage")

    assert any("source.storage.type" in error for error in errors)


def test_rejects_non_string_storage_type() -> None:
    validator = StorageConfigValidator(
        validators={
            "local": create_autospec(
                ComponentConfigValidator,
                instance=True,
            )
        }
    )

    errors = validator.validate(
        {"type": ["local"]},
        "source.storage",
    )

    assert any("source.storage.type" in error for error in errors)


def test_rejects_unsupported_storage_type() -> None:
    local_validator = create_autospec(
        ComponentConfigValidator,
        instance=True,
    )
    validator = StorageConfigValidator(validators={"local": local_validator})

    errors = validator.validate({"type": "unsupported"}, "source.storage")

    assert any("source.storage.type" in error for error in errors)
    assert any("local" in error for error in errors)
    local_validator.validate.assert_not_called()


def test_dispatches_to_the_validator_for_each_registered_type() -> None:
    local_validator = create_autospec(
        ComponentConfigValidator,
        instance=True,
    )
    s3_validator = create_autospec(
        ComponentConfigValidator,
        instance=True,
    )
    local_validator.validate.return_value = []
    s3_validator.validate.return_value = []

    validator = StorageConfigValidator(
        validators={
            "local": local_validator,
            "s3": s3_validator,
        }
    )
    config = {"type": "s3"}

    assert validator.validate(config, "source.storage") == []

    s3_validator.validate.assert_called_once_with(
        config,
        "source.storage",
    )
    local_validator.validate.assert_not_called()
