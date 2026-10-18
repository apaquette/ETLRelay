from collections.abc import Mapping
from typing import Final, cast

from etlrelay.config._validation import (
    as_mapping,
    validate_keys,
)
from etlrelay.processors.rename_columns import RenameColumns


class RenameColumnsConfigFactory:
    """Construct a RenameColumns processor from validated configuration."""

    def build(self, config: Mapping[str, object]) -> RenameColumns:
        """Build a processor using the configured column mapping."""
        return RenameColumns(
            mapping=cast(Mapping[str, str], config["mapping"]),
        )


class RenameColumnsConfigValidator:
    """Validate configuration for the RenameColumns processor."""

    _ALLOWED_KEYS: Final[frozenset[str]] = frozenset({"type", "mapping"})
    _REQUIRED_KEYS: Final[frozenset[str]] = frozenset({"type", "mapping"})

    def validate(self, config: object, path: str) -> list[str]:
        """Return validation errors for a RenameColumns configuration."""
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
