"""Configuration validation and construction for the RenameColumns processor.

This module provides a configuration validator and factory for constructing
RenameColumns processors from validated configuration mappings.
"""

from collections.abc import Mapping
from typing import Final, cast

from etlrelay.config._validation import (
    as_mapping,
    validate_keys,
)
from etlrelay.processors.rename_columns import RenameColumns


class RenameColumnsConfigFactory:
    """Construct RenameColumns processors from validated configuration."""

    def build(self, config: Mapping[str, object]) -> RenameColumns:
        """Build a RenameColumns processor from its configuration.

        Args:
            config: Validated configuration mapping containing the ``mapping``
                field, which associates source column names with target column
                names.

        Returns:
            A RenameColumns processor configured with the specified column
            mapping.

        Note:
            This method assumes the configuration has already been validated.
            The cast provides static type information and does not perform
            runtime validation.
        """
        return RenameColumns(
            mapping=cast(Mapping[str, str], config["mapping"]),
        )


class RenameColumnsConfigValidator:
    """Validate configuration mappings for the RenameColumns processor.

    The validator checks supported and required fields, the configured
    processor type, and the structure and value types of the column mapping.
    """

    _ALLOWED_KEYS: Final[frozenset[str]] = frozenset({"type", "mapping"})
    _REQUIRED_KEYS: Final[frozenset[str]] = frozenset({"type", "mapping"})

    def validate(self, config: object, path: str) -> list[str]:
        """Validate a RenameColumns configuration and report any errors.

        The configuration must be a mapping containing the required fields.
        The ``type`` field must be ``"rename_columns"``, and ``mapping`` must
        be a mapping with string keys and string values.

        Args:
            config: Configuration value to validate.
            path: Configuration path used to identify validation errors.

        Returns:
            A list of validation error messages. The list is empty when no
            validation errors are found.

        Note:
            This validator checks the mapping's structure and key/value types.
            It does not enforce non-empty column names or uniqueness of target
            column names.
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

        if "type" in mapping and mapping["type"] != "rename_columns":
            errors.append(f"{path}.type must be 'rename_columns'.")

        if "mapping" not in mapping:
            return errors

        column_mapping = mapping["mapping"]
        mapping_path = f"{path}.mapping"

        if not isinstance(column_mapping, Mapping):
            errors.append(f"{mapping_path} must be a mapping.")
            return errors

        for source, target in column_mapping.items():
            if not isinstance(source, str):
                errors.append(f"{mapping_path} keys must be strings.")
                continue

            if not isinstance(target, str):
                errors.append(f"{mapping_path}.{source} must be a string.")

        return errors
