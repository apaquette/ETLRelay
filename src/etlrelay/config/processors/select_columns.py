"""Configuration validation and construction for the SelectColumns processor.

This module provides a configuration validator and factory for constructing
SelectColumns processors from validated configuration mappings.
"""

from collections.abc import Mapping
from typing import Final, cast

from etlrelay.config._validation import (
    as_mapping,
    validate_keys,
)
from etlrelay.processors.select_columns import SelectColumns


class SelectColumnsConfigFactory:
    """Construct SelectColumns processors from validated configuration."""

    def build(self, config: Mapping[str, object]) -> SelectColumns:
        """Build a SelectColumns processor from its configuration.

        Args:
            config: Validated configuration mapping containing the ``columns``
                field, which specifies the column names in the desired order.

        Returns:
            A SelectColumns processor configured with the specified column
            sequence.

        Note:
            This method assumes the configuration has already been validated.
            The cast provides static type information and does not perform
            runtime validation.
        """
        return SelectColumns(
            columns=cast(list[str], config["columns"]),
        )


class SelectColumnsConfigValidator:
    """Validate configuration mappings for the SelectColumns processor.

    The validator checks supported and required fields, the configured
    processor type, and the structure and contents of the column list.
    """

    _ALLOWED_KEYS: Final[frozenset[str]] = frozenset({"type", "columns"})
    _REQUIRED_KEYS: Final[frozenset[str]] = frozenset({"type", "columns"})

    def validate(self, config: object, path: str) -> list[str]:
        """Validate a SelectColumns configuration and report any errors.

        The configuration must be a mapping containing the required fields.
        The ``type`` field must be ``"select_columns"``, and ``columns`` must
        be a list containing only unique string values.

        Args:
            config: Configuration value to validate.
            path: Configuration path used to identify validation errors.

        Returns:
            A list of validation error messages. The list is empty when no
            validation errors are found.

        Note:
            An empty list of columns is accepted by this validator. Whether
            selecting no columns is meaningful at runtime depends on the
            processor's behavior.
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
