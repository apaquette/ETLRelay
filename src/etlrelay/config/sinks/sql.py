from collections.abc import Mapping
from typing import Final, cast

from etlrelay.config._validation import (
    as_mapping,
    non_empty_string_error,
    validate_keys,
)
from etlrelay.config.sql_engine_factory import SqlEngineProvider
from etlrelay.sinks.sql import SqlSink


class SqlSinkConfigFactory:
    """Construct an existing SQL sink from validated configuration."""

    def __init__(self, engine_factory: SqlEngineProvider) -> None:
        self._engine_factory = engine_factory

    def build(self, config: Mapping[str, object]) -> SqlSink:
        """Construct a SQL sink using an engine resolved during preflight."""
        engine = self._engine_factory.create(cast(str, config["connection_url_env"]))
        return SqlSink(
            engine=engine,
            table_name=cast(str, config["table_name"]),
            schema=cast(str | None, config.get("schema")),
        )


class SqlSinkConfigValidator:
    _ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
        {
            "type",
            "connection_url_env",
            "table_name",
            "schema",
        }
    )
    _REQUIRED_KEYS: Final[frozenset[str]] = frozenset(
        {
            "type",
            "connection_url_env",
            "table_name",
        }
    )

    def validate(self, config: object, path: str) -> list[str]:
        mapping, errors = as_mapping(config, path)

        if mapping is None:
            return errors

        errors.extend(
            validate_keys(
                mapping,
                path,
                allowed=tuple(self._ALLOWED_KEYS),
                required=tuple(self._REQUIRED_KEYS),
            )
        )

        if errors:
            return errors

        if mapping["type"] != "sql":
            errors.append(f"{path}.type must be 'sql'.")

        for key in {"connection_url_env", "table_name"}:
            error = non_empty_string_error(mapping[key], f"{path}.{key}")
            if error is not None:
                errors.append(error)

        if "schema" in mapping:
            errors.extend(self._validate_schema(mapping, path))

        return errors

    def _validate_schema(self, mapping: Mapping[str, object], path: str) -> list[str]:
        schema = mapping["schema"]
        schema_path = f"{path}.schema"

        if not isinstance(schema, str) or not schema.strip():
            return [f"{schema_path} must be a string."]

        return []
