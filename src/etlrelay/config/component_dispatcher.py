"""Shared implementation for component configuration dispatch.

This module provides a dispatcher that validates the structure of a component
configuration, resolves its registered component type, and delegates validation
to the corresponding registered validator. It performs validation without
invoking component factories.
"""

from typing import Any

from etlrelay.config._validation import as_mapping
from etlrelay.config.registry import ComponentRegistry


class ComponentConfigDispatcher:
    """Dispatch component configuration validation by registered type.

    The dispatcher uses a component registry to resolve the validator associated
    with a configuration's ``type`` field. It rejects malformed configurations,
    missing or invalid type fields, and unregistered component types before
    delegating to the registered validator.
    """

    def __init__(
        self,
        registry: ComponentRegistry[Any],
        component_kind: str,
    ) -> None:
        """Initialize the dispatcher with a registry and component category.

        Args:
            registry: Registry containing the component registrations and their
                configuration validators.
            component_kind: Human-readable component category used in
                validation error messages, such as ``"source"`` or
                ``"processor"``.
        """
        self._registry = registry
        self._component_kind = component_kind

    def validate(self, config: object, path: str) -> list[str]:
        """Validate a component configuration using its registered validator.

        The method first checks that the configuration is a mapping with valid
        string keys and contains a non-empty string ``type`` field. It then
        resolves the component registration and delegates validation to its
        registered validator. Validation stops at the first dispatch-level
        failure.

        Args:
            config: Component configuration value to validate.
            path: Configuration path used to identify the location of
                validation errors.

        Returns:
            A list of validation error messages. The list contains errors for
            malformed mappings, invalid or missing type fields, unregistered
            component types, or errors reported by the registered validator.
            An empty list indicates that validation succeeded.

        Note:
            This method validates configuration only. It does not invoke the
            registered component factory or construct the component.
        """
        mapping, errors = as_mapping(config, path)

        if mapping is None or errors:
            return errors

        if "type" not in mapping:
            return [f"{path}.type is required."]

        component_type = mapping["type"]

        if not isinstance(component_type, str) or not component_type.strip():
            return [f"{path}.type must be a non-empty string."]

        try:
            registration = self._registry.get(component_type)
        except KeyError:
            return [
                f"{path}.type '{component_type}' is not a registered {self._component_kind} type."
            ]

        return registration.validator.validate(config, path)
