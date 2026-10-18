"""Unit tests for FilterRows configuration validation."""

import pytest

from etlrelay.config.processors.filter_rows import FilterRowsConfigValidator


def valid_config() -> dict[str, object]:
    return {
        "type": "filter_rows",
        "column": "amount",
        "operator": ">=",
        "value": 0,
    }


def test_accepts_valid_filter() -> None:
    assert FilterRowsConfigValidator().validate(valid_config(), "processors[0]") == []


@pytest.mark.parametrize("operator", ["==", "!=", "<", "<=", ">", ">="])
def test_accepts_supported_operators(operator: str) -> None:
    config = valid_config()
    config["operator"] = operator

    assert FilterRowsConfigValidator().validate(config, "processors[0]") == []


@pytest.mark.parametrize("value", ["ready", 1, 1.5, True, False])
def test_accepts_supported_scalar_values(value: object) -> None:
    config = valid_config()
    config["value"] = value

    assert FilterRowsConfigValidator().validate(config, "processors[0]") == []


def test_requires_all_properties() -> None:
    errors = FilterRowsConfigValidator().validate({}, "processors[0]")

    for field in ("type", "column", "operator", "value"):
        assert any(f"processors[0].{field}" in error for error in errors)


@pytest.mark.parametrize("column", ["", "   ", None, 3, True])
def test_column_must_be_non_empty_string(column: object) -> None:
    config = valid_config()
    config["column"] = column

    errors = FilterRowsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].column" in error for error in errors)


def test_rejects_unsupported_operator() -> None:
    config = valid_config()
    config["operator"] = "contains"

    errors = FilterRowsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].operator" in error for error in errors)


@pytest.mark.parametrize("value", [None, [], {}, (1, 2)])
def test_rejects_unsupported_filter_values(value: object) -> None:
    config = valid_config()
    config["value"] = value

    errors = FilterRowsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].value" in error for error in errors)


def test_rejects_unknown_properties() -> None:
    config = valid_config()
    config["case_sensitive"] = True

    errors = FilterRowsConfigValidator().validate(config, "processors[0]")

    assert any("processors[0].case_sensitive" in error for error in errors)


def test_rejects_non_mapping_configuration() -> None:
    errors = FilterRowsConfigValidator().validate(None, "processors[0]")

    assert any("processors[0]" in error and "mapping" in error.lower() for error in errors)


def test_rejects_non_string_property_keys() -> None:
    config: dict[object, object] = {
        "type": "filter_rows",
        "column": "amount",
        "operator": ">=",
        "value": 0,
        1: "unexpected",
    }

    errors = FilterRowsConfigValidator().validate(config, "processors[0]")

    assert errors
    assert all(isinstance(error, str) for error in errors)
