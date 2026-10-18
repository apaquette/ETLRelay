"""Unit tests for SelectColumns configuration validation."""

import pytest

from etlrelay.config.processors.select_columns import SelectColumnsConfigValidator


def test_accepts_unique_string_columns() -> None:
    config: dict[str, object] = {
        "type": "select_columns",
        "columns": ["id", "name"],
    }

    assert SelectColumnsConfigValidator().validate(config, "processors[0]") == []


def test_accepts_empty_column_list() -> None:
    config: dict[str, object] = {"type": "select_columns", "columns": []}

    assert SelectColumnsConfigValidator().validate(config, "processors[0]") == []


def test_requires_type_and_columns() -> None:
    errors = SelectColumnsConfigValidator().validate({}, "processors[0]")

    assert any("processors[0].type" in error for error in errors)
    assert any("processors[0].columns" in error for error in errors)


def test_rejects_wrong_processor_type() -> None:
    config: dict[str, object] = {"type": "filter_rows", "columns": ["id"]}

    errors = SelectColumnsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].type" in error for error in errors)


@pytest.mark.parametrize("columns", ["id", None, 7, {"id": True}])
def test_columns_must_be_a_list(columns: object) -> None:
    config: dict[str, object] = {"type": "select_columns", "columns": columns}

    errors = SelectColumnsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].columns" in error for error in errors)


def test_column_names_must_be_strings() -> None:
    config: dict[str, object] = {
        "type": "select_columns",
        "columns": ["id", 2],
    }

    errors = SelectColumnsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].columns" in error for error in errors)


def test_column_names_must_be_unique() -> None:
    config: dict[str, object] = {
        "type": "select_columns",
        "columns": ["id", "id"],
    }

    errors = SelectColumnsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].columns" in error and "unique" in error.lower() for error in errors)


def test_rejects_unknown_properties() -> None:
    config: dict[str, object] = {
        "type": "select_columns",
        "columns": ["id"],
        "case_sensitive": True,
    }

    errors = SelectColumnsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].case_sensitive" in error for error in errors)


def test_rejects_non_mapping_configuration() -> None:
    errors = SelectColumnsConfigValidator().validate([], "processors[0]")

    assert any("processors[0]" in error and "mapping" in error.lower() for error in errors)


def test_rejects_non_string_property_keys() -> None:
    config: dict[object, object] = {
        "type": "select_columns",
        "columns": ["id"],
        1: "unexpected",
    }

    errors = SelectColumnsConfigValidator().validate(config, "processors[0]")

    assert errors
    assert all(isinstance(error, str) for error in errors)
