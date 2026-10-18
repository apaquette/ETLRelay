"""Configuration validation and construction for file sources.

This module provides a factory for constructing FileSource instances and a
validator for checking file source configuration, including the selected
tabular file format and nested storage configuration.
"""

from collections.abc import Mapping
from typing import Any

from etlrelay.config._validation import (
    as_mapping,
    non_empty_string_error,
    validate_keys,
)
from etlrelay.config.component_validator import ComponentConfigValidator
from etlrelay.config.registry import ComponentRegistry
from etlrelay.file_formats import TabularFileFormatRegistry
from etlrelay.sources import FileSource
from etlrelay.storage import FileSystem


class FileSourceConfigFactory:
    """Construct file sources from validated configuration mappings.

    The factory resolves the configured storage component and obtains a reader
    for the selected file format before constructing the FileSource.
    """

    def __init__(
        self,
        storage_registry: ComponentRegistry[FileSystem],
        format_registry: TabularFileFormatRegistry,
    ) -> None:
        """Initialize the factory with storage and file-format registries.

        Args:
            storage_registry: Registry containing storage component
                registrations and their factories.
            format_registry: Registry used to create readers for supported
                tabular file formats.
        """
        self._storage_registry = storage_registry
        self._format_registry = format_registry

    def build(self, config: Mapping) -> FileSource:
        """Build a file source from its configuration.

        Args:
            config: Validated configuration mapping containing the input
                ``path``, a nested ``storage`` configuration, and a ``format``
                identifying the input file format.

        Returns:
            A FileSource configured with the specified input path, storage
            implementation, and format reader.

        Note:
            This method assumes the configuration has already been validated.
            It does not independently validate required fields or confirm that
            the selected storage and format are supported.
        """
        path = config["path"]
        storage = self._storage_registry.get(config["storage"]["type"]).factory.build(
            config["storage"]
        )
        reader = self._format_registry.create_reader(config["format"])
        return FileSource(path=path, storage=storage, reader=reader)


class FileSourceConfigValidator:
    """Validate file source configuration and nested storage settings.

    The validator checks supported and required fields, the source type, the
    input path, and format read support. It delegates nested storage validation
    to the supplied storage validator.
    """

    def __init__(
        self,
        format_registry: TabularFileFormatRegistry[Any, Any],
        storage_validator: ComponentConfigValidator,
    ) -> None:
        """Initialize the validator with format and storage dependencies.

        Args:
            format_registry: Registry used to determine whether a file format
                supports reading.
            storage_validator: Validator responsible for checking the nested
                storage component configuration.
        """
        self._format_registry = format_registry
        self._storage_validator = storage_validator

    def validate(self, config: object, path: str) -> list[str]:
        """Validate file source configuration and return any errors.

        The configuration must be a mapping containing ``type``, ``path``,
        ``format``, and ``storage``. The type must be ``"file"``, the path
        must be a non-empty string, and the format must be a non-empty string
        supported for reading by the format registry. Nested storage
        configuration is validated by the supplied storage validator.

        Args:
            config: Configuration value to validate.
            path: Configuration path used to identify validation errors.

        Returns:
            A list of validation error messages. The list is empty when
            validation finds no errors. Errors may identify unsupported or
            missing fields, invalid field values, unsupported input formats,
            or invalid nested storage configuration.
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
                errors.append(f"{path}.format must be a non-empty string.")
            elif not self._format_registry.supports_reading(format_name):
                errors.append(f"{path}.format '{format_name}' is not supported for reading.")

        if "storage" in mapping:
            errors.extend(
                self._storage_validator.validate(
                    mapping["storage"],
                    f"{path}.storage",
                )
            )

        return errors
