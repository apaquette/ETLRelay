"""Validate storage configuration by dispatching to storage-specific validators."""

from collections.abc import Mapping
from typing import Any

from etlrelay.config.validator import ComponentConfigValidator


class StorageConfigValidator:
    """Dispatch storage configuration validation by storage type.

    This validator checks that the configuration is a mapping, contains a
    string-valued ``type`` property, and specifies a supported storage type.
    It delegates storage-specific property validation to the corresponding
    registered validator.

    Attributes:
        _validators: Mapping of supported storage type names to their
            configuration validators.
    """

    def __init__(
        self,
        validators: Mapping[str, ComponentConfigValidator],
    ) -> None:
        """Initialize the storage validator with supported type validators.

        Args:
            validators: Mapping from storage type names, such as ``local``,
                to validators implementing ``ComponentConfigValidator``.

        The supplied mapping defines which storage types are supported.
        """
        self._validators = validators

    def validate(self, config: Any, path: str) -> list[str]:
        """Validate storage configuration and delegate type-specific checks.

        Args:
            config: Parsed storage configuration to validate.
            path: Configuration path used to qualify error messages, such as
                ``source.storage`` or ``sink.storage``.

        Returns:
            A list of validation error messages. An empty list indicates that
            validation succeeded.

        Validation stops and returns an error if the configuration is not a
        mapping, the ``type`` property is missing or is not a string, or the
        specified storage type is unsupported. Otherwise, validation is
        delegated to the validator registered for that type.
        """
        if not isinstance(config, Mapping):
            return [f"{path} must be a mapping"]

        if "type" not in config:
            return [f"{path}.type is required"]

        storage_type = config.get("type")
        if not isinstance(storage_type, str):
            return [f"{path}.type must be of type string"]

        if storage_type not in self._validators:
            supported_types = ", ".join(self._validators)
            return [
                f"{path}.type {storage_type} is unsupported. Supported types: {supported_types}"
            ]

        validator = self._validators[storage_type]
        return validator.validate(config, path)
