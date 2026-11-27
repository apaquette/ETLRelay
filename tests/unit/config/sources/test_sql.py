"""Contract tests for SQL source configuration validation."""

import pytest

from etlrelay.config.sources import SqlSourceConfigValidator


@pytest.fixture
def validator() -> SqlSourceConfigValidator:
    return SqlSourceConfigValidator()


def valid_source() -> dict[str, object]:
    return {
        "type": "sql",
        "connection_url_env": "ETLRELAY_SOURCE_DATABASE_URL",
        "query": "SELECT id FROM records",
    }


def test_accepts_minimal_sql_source(validator: SqlSourceConfigValidator) -> None:
    assert validator.validate(valid_source(), "source") == []


def test_accepts_scalar_query_parameters(validator: SqlSourceConfigValidator) -> None:
    config = valid_source()
    config["parameters"] = {
        "name": "Ada",
        "age": 37,
        "ratio": 1.25,
        "active": True,
        "optional": None,
    }

    assert validator.validate(config, "source") == []


def test_does_not_resolve_environment_variable(
    validator: SqlSourceConfigValidator, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validation checks the variable name; resolution belongs to the builder."""
    monkeypatch.delenv("ETLRELAY_TEST_UNSET_DATABASE_URL", raising=False)
    config = valid_source()
    config["connection_url_env"] = "ETLRELAY_TEST_UNSET_DATABASE_URL"

    assert validator.validate(config, "source") == []


def test_requires_type_connection_variable_and_query(
    validator: SqlSourceConfigValidator,
) -> None:
    errors = validator.validate({}, "source")

    for field in ("type", "connection_url_env", "query"):
        assert any(f"source.{field}" in error for error in errors)


@pytest.mark.parametrize("field", ["connection_url_env", "query"])
@pytest.mark.parametrize("value", [None, "", " \t ", 3, True])
def test_required_sql_strings_must_be_non_empty_strings(
    validator: SqlSourceConfigValidator, field: str, value: object
) -> None:
    config = valid_source()
    config[field] = value

    errors = validator.validate(config, "source")

    assert any(f"source.{field}" in error for error in errors)


def test_rejects_wrong_component_type(validator: SqlSourceConfigValidator) -> None:
    config = valid_source()
    config["type"] = "file"

    assert any("source.type" in error for error in validator.validate(config, "source"))


def test_rejects_unknown_properties(validator: SqlSourceConfigValidator) -> None:
    config = valid_source()
    config["timeout"] = 30

    errors = validator.validate(config, "source")

    assert any("source.timeout" in error for error in errors)


@pytest.mark.parametrize("value", ["not-a-mapping", ["value"], 42])
def test_parameters_must_be_a_mapping(validator: SqlSourceConfigValidator, value: object) -> None:
    config = valid_source()
    config["parameters"] = value

    errors = validator.validate(config, "source")

    assert any("source.parameters" in error for error in errors)


def test_parameter_names_must_be_strings(validator: SqlSourceConfigValidator) -> None:
    config = valid_source()
    config["parameters"] = {1: "value"}

    errors = validator.validate(config, "source")

    assert any("source.parameters" in error for error in errors)


@pytest.mark.parametrize("value", [[1], {"nested": "value"}, ("tuple",)])
def test_parameter_values_must_be_yaml_scalars(
    validator: SqlSourceConfigValidator, value: object
) -> None:
    config = valid_source()
    config["parameters"] = {"invalid": value}

    errors = validator.validate(config, "source")

    assert any("source.parameters.invalid" in error for error in errors)


def test_rejects_non_mapping_source(validator: SqlSourceConfigValidator) -> None:
    for value in (None, [], "source", 42):
        errors = validator.validate(value, "source")
        assert any("source" in error and "mapping" in error for error in errors)


def test_rejects_non_string_property_keys(validator: SqlSourceConfigValidator) -> None:
    config: dict[object, object] = {**valid_source(), 1: "unexpected"}

    errors = validator.validate(config, "source")

    assert errors
    assert all(isinstance(error, str) for error in errors)


@pytest.mark.parametrize("value", [100, 1, 10, 50, 17])
def test_accepts_valid_batch_size_values(
    validator: SqlSourceConfigValidator, value: object
) -> None:
    config = valid_source()
    config["batch_size"] = value

    errors = validator.validate(config, "source")

    assert not errors


@pytest.mark.parametrize(
    "value", [[1], {"nested": "value"}, ("tuple",), 0, -10, True, "invalid", 5.5]
)
def test_rejects_invalid_batch_size_values(
    validator: SqlSourceConfigValidator, value: object
) -> None:
    config = valid_source()
    config["batch_size"] = value

    errors = validator.validate(config, "source")

    assert errors
    assert any("batch_size" in error for error in errors)


def test_accepts_nullable_or_omitted_arrow_schema(validator: SqlSourceConfigValidator) -> None:
    config = valid_source()
    config["schema"] = None

    assert validator.validate(config, "source") == []


def test_accepts_declarative_arrow_schema(validator: SqlSourceConfigValidator) -> None:
    config = valid_source()
    config["schema"] = {
        "fields": [
            {"name": "id", "type": "int64", "nullable": False},
            {"name": "name", "type": "string"},
            {"name": "created_at", "type": "timestamp"},
        ]
    }

    assert validator.validate(config, "source") == []


@pytest.mark.parametrize("value", [42, True, {"type": "select"}, ["SELECT 1"]])
def test_yaml_query_must_be_sql_text(
    validator: SqlSourceConfigValidator, value: object
) -> None:
    config = valid_source()
    config["query"] = value

    errors = validator.validate(config, "source")

    assert any("source.query" in error for error in errors)


@pytest.mark.parametrize(
    "schema",
    [
        [],
        {"fields": []},
        {"unexpected": []},
        {"fields": [{"name": "id"}]},
        {"fields": [{"name": "id", "type": "decimal"}]},
        {"fields": [{"name": "id", "type": "int64", "nullable": "yes"}]},
        {
            "fields": [
                {"name": "id", "type": "int64"},
                {"name": "id", "type": "string"},
            ]
        },
        {"fields": [{"name": "", "type": "int64"}]},
        {"fields": ["not-a-field"]},
    ],
)
def test_rejects_invalid_arrow_schema(
    validator: SqlSourceConfigValidator, schema: object
) -> None:
    config = valid_source()
    config["schema"] = schema

    errors = validator.validate(config, "source")

    assert errors
    assert any("source.schema" in error for error in errors)


def test_rejects_unknown_sql_source_property(
    validator: SqlSourceConfigValidator,
) -> None:
    config = valid_source()
    config["driver"] = "psycopg"

    errors = validator.validate(config, "source")

    assert any("source.driver" in error for error in errors)


def test_custom_validation_path_is_preserved(
    validator: SqlSourceConfigValidator,
) -> None:
    config = valid_source()
    config["batch_size"] = 0

    errors = validator.validate(config, "pipeline.source")

    assert any("pipeline.source.batch_size" in error for error in errors)
