"""Configuration validation for SQL-backed data sources."""

from collections.abc import Mapping
from typing import Final

from etlrelay.config._validation import (
    as_mapping,
    non_empty_string_error,
    validate_keys,
)


class SqlSourceConfigValidator:
    """Validate SQL source configuration without performing I/O."""

    _ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
        {
            "type",
            "connection_url_env",
            "query",
            "parameters",
        }
    )

    _REQUIRED_KEYS: Final[frozenset[str]] = frozenset(
        {
            "type",
            "connection_url_env",
            "query",
        }
    )

    _SCALAR_TYPES: Final[tuple[type, ...]] = (str, int, float, bool)

    def validate(self, config: object, path: str) -> list[str]:
        """Return validation errors for a SQL source configuration."""
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

        for key in {"connection_url_env", "query"}:
            error = non_empty_string_error(mapping[key], f"{path}.{key}")
            if error is not None:
                errors.append(error)

        if "parameters" in mapping:
            errors.extend(self._validate_parameters(mapping, path))

        return errors

    def _validate_parameters(self, mapping: Mapping[str, object], path: str) -> list[str]:
        errors = []
        parameters_path = f"{path}.parameters"

        if not isinstance(mapping["parameters"], Mapping):
            errors.append(f"{parameters_path} must be a mapping.")
            return errors

        for name, value in mapping["parameters"].items():
            if not isinstance(name, str):
                errors.append(f"{parameters_path} keys must be strings.")
                continue

            if value is not None and type(value) not in self._SCALAR_TYPES:
                errors.append(
                    f"{parameters_path}.{name} must be a scalar "
                    "string, integer, float, boolean, or null."
                )

        return errors
