from collections.abc import Mapping
from typing import Final

from etlrelay.config._validation import (
    as_mapping,
    non_empty_string_error,
    validate_keys,
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
