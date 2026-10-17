"""Configuration validator for file sinks."""

from typing import Any

from etlrelay.config._validation import (
    as_mapping,
    non_empty_string_error,
    validate_keys,
)
from etlrelay.config.component_validator import ComponentConfigValidator
from etlrelay.file_formats import TabularFileFormatRegistry


class FileSinkConfigValidator:
    """Validate file sink configuration and its nested storage settings."""

    def __init__(
        self,
        format_registry: TabularFileFormatRegistry[Any, Any],
        storage_validator: ComponentConfigValidator,
    ) -> None:
        """Initialize the validator with format and storage registries."""
        self._format_registry = format_registry
        self._storage_validator = storage_validator

    def validate(self, config: object, path: str) -> list[str]:
        """Validate file sink settings and return any errors.

        Supported formats are determined by the file-format registry's
        writing capabilities. Nested storage configuration is delegated to
        the supplied storage validator.
        """
        mapping, errors = as_mapping(config, path)
        if mapping is None:
            return errors

        errors.extend(
            validate_keys(
                mapping,
                path,
                allowed=("type", "path", "format", "storage"),
                required=("type", "path", "format", "storage"),
            )
        )

        if "type" in mapping and mapping["type"] != "file":
            errors.append(f"{path}.type must be 'file'.")

        if "path" in mapping:
            error = non_empty_string_error(mapping["path"], f"{path}.path")
            if error is not None:
                errors.append(error)

        if "format" in mapping:
            format_name = mapping["format"]

            if not isinstance(format_name, str) or not format_name.strip():
                errors.append(
                    f"{path}.format must be a non-empty string."
                )
            elif not self._format_registry.supports_writing(format_name):
                errors.append(
                    f"{path}.format '{format_name}' is not supported "
                    "for writing."
                )

        if "storage" in mapping:
            errors.extend(
                self._storage_validator.validate(
                    mapping["storage"],
                    f"{path}.storage",
                )
            )

        return errors