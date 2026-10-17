"""Shared implementation for component configuration dispatch."""

from typing import Any

from etlrelay.config._validation import as_mapping
from etlrelay.config.registry import ComponentRegistry


class ComponentConfigDispatcher:
    """Select a component validator using its configuration type."""

    def __init__(
        self,
        registry: ComponentRegistry[Any],
        component_kind: str,
    ) -> None:
        """Initialize the dispatcher with a registry and component category."""
        self._registry = registry
        self._component_kind = component_kind

    def validate(self, config: object, path: str) -> list[str]:
        """Dispatch validation to the registered validator.

        Reject malformed mappings and invalid or unregistered component types
        before delegating validation. Component factories are never invoked.
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
