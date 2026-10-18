from collections.abc import Mapping
from typing import Final, cast

from etlrelay.config._validation import (
    as_mapping,
    validate_keys,
)
from etlrelay.processors.select_columns import SelectColumns


class SelectColumnsConfigFactory:
    """Construct a SelectColumns processor from validated configuration."""

    def build(self, config: Mapping[str, object]) -> SelectColumns:
        """Build a processor using the configured column order."""
        return SelectColumns(
            columns=cast(list[str], config["columns"]),
        )


class SelectColumnsConfigValidator:
    """Validate configuration for the SelectColumns processor."""

    _ALLOWED_KEYS: Final[frozenset[str]] = frozenset({"type", "columns"})
    _REQUIRED_KEYS: Final[frozenset[str]] = frozenset({"type", "columns"})

    def validate(self, config: object, path: str) -> list[str]:
        """Return validation errors for a SelectColumns configuration."""
        mapping, errors = as_mapping(config, path)
        if mapping is None:
            return errors

        errors.extend(
            validate_keys(
                config=mapping,
                path=path,
                allowed=tuple(self._ALLOWED_KEYS),
                required=tuple(self._REQUIRED_KEYS),
            )
        )

        if "type" in mapping and mapping["type"] != "select_columns":
            errors.append(f"{path}.type must be 'select_columns'.")

        if "columns" not in mapping:
            return errors

        columns = mapping["columns"]
        columns_path = f"{path}.columns"

        if not isinstance(columns, list):
            errors.append(f"{columns_path} must be a list of strings.")
            return errors

        if any(not isinstance(column, str) for column in columns):
            errors.append(f"{columns_path} must contain only strings.")
            return errors

        if len(columns) != len(set(columns)):
            errors.append(f"{columns_path} must contain unique column names.")

        return errors
