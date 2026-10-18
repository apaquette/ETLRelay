"""Contract tests for SQL sink configuration validation."""

import pytest

from etlrelay.config.sinks import SqlSinkConfigValidator


@pytest.fixture
def validator() -> SqlSinkConfigValidator:
    return SqlSinkConfigValidator()


def valid_sink() -> dict[str, object]:
    return {
        "type": "sql",
        "connection_url_env": "ETLRELAY_SINK_DATABASE_URL",
        "table_name": "processed_records",
    }


def test_accepts_minimal_sql_sink(validator: SqlSinkConfigValidator) -> None:
    assert validator.validate(valid_sink(), "sink") == []


def test_accepts_optional_schema(validator: SqlSinkConfigValidator) -> None:
    config = valid_sink()
    config["schema"] = "analytics"

    assert validator.validate(config, "sink") == []


def test_does_not_resolve_environment_variable(
    validator: SqlSinkConfigValidator, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validation checks the variable name; resolution belongs to the builder."""
    monkeypatch.delenv("ETLRELAY_TEST_UNSET_DATABASE_URL", raising=False)
    config = valid_sink()
    config["connection_url_env"] = "ETLRELAY_TEST_UNSET_DATABASE_URL"

    assert validator.validate(config, "sink") == []


def test_requires_type_connection_variable_and_table_name(
    validator: SqlSinkConfigValidator,
) -> None:
    errors = validator.validate({}, "sink")

    for field in ("type", "connection_url_env", "table_name"):
        assert any(f"sink.{field}" in error for error in errors)


@pytest.mark.parametrize("field", ["connection_url_env", "table_name", "schema"])
@pytest.mark.parametrize("value", [None, "", " \t ", 3, True])
def test_name_fields_must_be_non_empty_strings(
    validator: SqlSinkConfigValidator, field: str, value: object
) -> None:
    config = valid_sink()
    config[field] = value

    errors = validator.validate(config, "sink")

    assert any(f"sink.{field}" in error for error in errors)


def test_rejects_wrong_component_type(validator: SqlSinkConfigValidator) -> None:
    config = valid_sink()
    config["type"] = "file"

    assert any("sink.type" in error for error in validator.validate(config, "sink"))


def test_rejects_unknown_properties(validator: SqlSinkConfigValidator) -> None:
    config = valid_sink()
    config["if_exists"] = "replace"

    errors = validator.validate(config, "sink")

    assert any("sink.if_exists" in error for error in errors)


def test_rejects_non_mapping_sink(validator: SqlSinkConfigValidator) -> None:
    for value in (None, [], "sink", 42):
        errors = validator.validate(value, "sink")
        assert any("sink" in error and "mapping" in error for error in errors)


def test_rejects_non_string_property_keys(validator: SqlSinkConfigValidator) -> None:
    config: dict[object, object] = {**valid_sink(), 1: "unexpected"}

    errors = validator.validate(config, "sink")

    assert errors
    assert all(isinstance(error, str) for error in errors)
