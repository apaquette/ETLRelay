"""Configuration validation and construction for the FilterRows processor.

This module provides a configuration validator and factory for creating
FilterRows processors from validated configuration mappings.
"""

from collections.abc import Mapping
from typing import Final, cast

from etlrelay.config._validation import (
    as_mapping,
    non_empty_string_error,
    validate_keys,
)
from etlrelay.processors.filter_rows import FilterRows


class FilterRowsConfigFactory:
    """Construct FilterRows processors from validated configuration mappings."""

    def build(self, config: Mapping[str, object]) -> FilterRows:
        """Build a FilterRows processor from its configuration.

        Args:
            config: Validated configuration mapping containing the ``column``,
                ``operator``, and ``value`` fields.

        Returns:
            A FilterRows processor configured with the specified predicate.

        Note:
            This method assumes the configuration has already been validated.
            It does not independently check field presence or value types.
        """
        return FilterRows(
            column=cast(str, config["column"]),
            operator=cast(str, config["operator"]),
            value=cast(str | int | float | bool, config["value"]),
        )


class FilterRowsConfigValidator:
    """Validate configuration mappings for the FilterRows processor.

    The validator checks the supported and required fields, the configured
    processor type, the column name, the comparison operator, and the
    predicate value's type.
    """

    _ALLOWED_KEYS: Final[frozenset[str]] = frozenset({"type", "column", "operator", "value"})
    _REQUIRED_KEYS: Final[frozenset[str]] = frozenset({"type", "column", "operator", "value"})
    _SUPPORTED_OPERATORS: Final[frozenset[str]] = frozenset({"==", "!=", "<", "<=", ">", ">="})

    def validate(self, config: object, path: str) -> list[str]:
        """Validate a FilterRows configuration and report any errors.

        The configuration must be a mapping containing the required fields.
        The ``type`` field must be ``"filter_rows"``, ``column`` must be a
        non-empty string, ``operator`` must be a supported comparison
        operator, and ``value`` must be a string, integer, float, or boolean.

        Args:
            config: Configuration value to validate.
            path: Configuration path used to identify validation errors.

        Returns:
            A list of validation error messages. The list is empty when no
            validation errors are found.
        """
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
