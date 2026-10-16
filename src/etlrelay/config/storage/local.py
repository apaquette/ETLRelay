"""Validate configuration for local filesystem storage."""

from collections.abc import Mapping
from typing import Any


class LocalFileSystemValidator:
    """Validate configuration properties for local filesystem storage.

    This validator checks the structure and supported properties of a local
    storage configuration. It does not access the filesystem or validate
    path containment at runtime.

    Required properties:
        type: Must be "local".

    Optional properties:
        base_path: A non-empty string defining the storage base directory.
    """

    required_properties = {"type"}
    optional_properties = {"base_path"}

    def validate(self, config: Any, path: str) -> list[str]:
        """Validate a local filesystem storage configuration.

        The configuration must be a mapping containing the required `type`
        property. Only the required and optional properties defined by this
        validator are accepted.

        Args:
            config: The parsed storage configuration to validate.
            path: The configuration location used to qualify error messages,
                such as "source.storage" or "sink.storage".

        Returns:
            A list of validation error messages. Each message identifies the
            relevant configuration location when applicable. An empty list
            indicates that no validation errors were found.

        Notes:
            If the configuration is not a mapping or a required property is
            missing, validation returns immediately with the corresponding
            error. Otherwise, unsupported properties, an invalid storage
            type, and an invalid base path are reported.

            This method performs configuration validation only. It does not
            instantiate storage components, access files, or enforce
            filesystem path containment.
        """
        if not isinstance(config, Mapping):
            return [f"{path} must be a mapping"]

        errors: list[str] = []

        missing = self.required_properties - config.keys()
        if missing:
            return [f"{path} required property missing: {', '.join(missing)}"]

        unknown = config.keys() - (self.required_properties | self.optional_properties)
        for key in unknown:
            errors.append(f"{path}.{str(key)}: unknown property")

        if config["type"] != "local":
            errors.append(f"{path}.type must be 'local'; got {config['type']!r}")

        if "base_path" in config and (
            not isinstance(config.get("base_path"), str)
            or not (str(config.get("base_path")).strip())
        ):
            errors.append(f"{path}.base_path must be a non-empty string")

        return errors
