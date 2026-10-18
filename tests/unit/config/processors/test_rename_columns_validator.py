"""Unit tests for RenameColumns configuration validation."""

from etlrelay.config.processors.rename_columns import RenameColumnsConfigValidator


def test_accepts_string_to_string_mapping() -> None:
    config: dict[str, object] = {
        "type": "rename_columns",
        "mapping": {"id": "record_id"},
    }

    assert RenameColumnsConfigValidator().validate(config, "processors[0]") == []


def test_accepts_empty_mapping() -> None:
    config: dict[str, object] = {"type": "rename_columns", "mapping": {}}

    assert RenameColumnsConfigValidator().validate(config, "processors[0]") == []


def test_requires_type_and_mapping() -> None:
    errors = RenameColumnsConfigValidator().validate({}, "processors[0]")

    assert any("processors[0].type" in error for error in errors)
    assert any("processors[0].mapping" in error for error in errors)


def test_rejects_wrong_processor_type() -> None:
    config: dict[str, object] = {
        "type": "select_columns",
        "mapping": {"id": "record_id"},
    }

    errors = RenameColumnsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].type" in error for error in errors)


def test_mapping_must_be_a_mapping() -> None:
    config: dict[str, object] = {
        "type": "rename_columns",
        "mapping": [["id", "record_id"]],
    }

    errors = RenameColumnsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].mapping" in error for error in errors)


def test_mapping_keys_must_be_strings() -> None:
    config: dict[str, object] = {
        "type": "rename_columns",
        "mapping": {1: "record_id"},
    }

    errors = RenameColumnsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].mapping" in error for error in errors)


def test_mapping_values_must_be_strings() -> None:
    config: dict[str, object] = {
        "type": "rename_columns",
        "mapping": {"id": 7},
    }

    errors = RenameColumnsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].mapping.id" in error for error in errors)


def test_rejects_unknown_properties() -> None:
    config: dict[str, object] = {
        "type": "rename_columns",
        "mapping": {"id": "record_id"},
        "columns": ["id"],
    }

    errors = RenameColumnsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].columns" in error for error in errors)


def test_rejects_non_mapping_configuration() -> None:
    errors = RenameColumnsConfigValidator().validate(None, "processors[0]")

    assert any("processors[0]" in error and "mapping" in error.lower() for error in errors)


def test_rejects_non_string_property_keys() -> None:
    config: dict[object, object] = {
        "type": "rename_columns",
        "mapping": {"id": "record_id"},
        1: "unexpected",
    }

    errors = RenameColumnsConfigValidator().validate(config, "processors[0]")

    assert errors
    assert all(isinstance(error, str) for error in errors)
