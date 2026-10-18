from collections.abc import Mapping
from typing import Final, cast

from etlrelay.config._validation import (
    as_mapping,
    non_empty_string_error,
    validate_keys,
)
from etlrelay.processors.filter_rows import FilterRows


class FilterRowsConfigFactory:
    """Construct a FilterRows processor from validated configuration."""

    def build(self, config: Mapping[str, object]) -> FilterRows:
        """Build a processor using the configured predicate."""
        return FilterRows(
            column=cast(str, config["column"]),
            operator=cast(str, config["operator"]),
            value=cast(str | int | float | bool, config["value"]),
        )


class FilterRowsConfigValidator:
    """Validate configuration for the FilterRows processor."""

    _ALLOWED_KEYS: Final[frozenset[str]] = frozenset({"type", "column", "operator", "value"})
    _REQUIRED_KEYS: Final[frozenset[str]] = frozenset({"type", "column", "operator", "value"})
    _SUPPORTED_OPERATORS: Final[frozenset[str]] = frozenset({"==", "!=", "<", "<=", ">", ">="})

    def validate(self, config: object, path: str) -> list[str]:
        """Return validation errors for a FilterRows configuration."""
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

        if "type" in mapping and mapping["type"] != "filter_rows":
            errors.append(f"{path}.type must be 'filter_rows'.")

        if "column" in mapping:
            error = non_empty_string_error(
                mapping["column"],
                f"{path}.column",
            )
            if error is not None:
                errors.append(error)

        if "operator" in mapping:
            operator = mapping["operator"]

            if not isinstance(operator, str) or operator not in self._SUPPORTED_OPERATORS:
                errors.append(f"{path}.operator must be one of '==', '!=', '<', '<=', '>', '>='.")

        if "value" in mapping:
            value = mapping["value"]

            if type(value) not in (str, int, float, bool):
                errors.append(f"{path}.value must be a string, integer, float, or boolean.")

        return errors
