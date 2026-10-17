"""Dispatcher for source configuration validation."""

from typing import Any

from etlrelay.config.component_dispatcher import ComponentConfigDispatcher
from etlrelay.config.registry import ComponentRegistry


class SourceConfigValidator(ComponentConfigDispatcher):
    """Dispatch source configuration to its registered validator."""

    def __init__(self, registry: ComponentRegistry[Any]) -> None:
        """Initialize the source validator registry."""
        super().__init__(registry, component_kind="source")
