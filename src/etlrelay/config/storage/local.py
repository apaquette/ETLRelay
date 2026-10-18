"""Configuration validation and construction for local filesystem storage.

This module provides a factory for constructing LocalFileSystem instances and
a validator for checking local storage configuration without accessing the
filesystem during validation.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import cast

from etlrelay.config._validation import (
    as_mapping,
    non_empty_string_error,
    validate_keys,
)
from etlrelay.security import PathValidator
from etlrelay.storage import LocalFileSystem


class LocalFileSystemConfigFactory:
    """Construct local filesystem storage from validated configuration.

    The factory creates a PathValidator using the configured base path and
    supplies it to the LocalFileSystem instance. When ``base_path`` is omitted,
    the current working directory is used.
    """

    def build(self, config: Mapping[str, object]) -> LocalFileSystem:
        """Build local filesystem storage from its configuration.

        Args:
            config: Validated configuration mapping containing the optional
                ``base_path`` field. When omitted, ``base_path`` defaults
                to ``"."``, representing the current working directory.

        Returns:
            A LocalFileSystem instance configured with a PathValidator for
            the selected base path.

        Note:
            This method assumes the configuration has already been validated.
            It does not independently validate the type or contents of
            ``base_path``.
        """
        base_path = Path(cast(str, config.get("base_path", ".")))
        path_validator = PathValidator(base_path=base_path)

        return LocalFileSystem(path_validator=path_validator)


class LocalFileSystemConfigValidator:
    """Validate configuration mappings for local filesystem storage.

    The validator checks supported and required fields, the storage type, and
    the optional base path. It validates configuration structure and value
    types without accessing the filesystem.
    """

    def validate(self, config: object, path: str) -> list[str]:
        """Validate local filesystem storage configuration.

        The configuration must be a mapping containing ``type`` with the value
        ``"local"``. The optional ``base_path`` field must be a non-empty
        string when present. If omitted, the factory uses the current working
        directory as the base path.

        Args:
            config: Configuration value to validate.
            path: Configuration path used to identify validation errors.

        Returns:
            A list of validation error messages. The list is empty when
            validation finds no errors. Errors may identify malformed
            configuration, unsupported or missing fields, an incorrect
            storage type, or an invalid base path.

        Note:
            Validation does not check whether the base path exists, is
            accessible, or can be used for filesystem operations.
        """
        mapping, errors = as_mapping(config, path)
        if mapping is None:
            return errors

        errors.extend(
            validate_keys(
                mapping,
                path,
                allowed=("type", "base_path"),
                required=("type",),
            )
        )

        if "type" in mapping and mapping["type"] != "local":
            errors.append(f"{path}.type must be 'local'.")

        if "base_path" in mapping:
            error = non_empty_string_error(
                mapping["base_path"],
                f"{path}.base_path",
            )
            if error is not None:
                errors.append(error)

        return errors
