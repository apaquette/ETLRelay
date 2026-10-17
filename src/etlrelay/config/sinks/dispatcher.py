"""Dispatcher for sink configuration validation."""

from typing import Any

from etlrelay.config.component_dispatcher import ComponentConfigDispatcher
from etlrelay.config.registry import ComponentRegistry


class SinkConfigValidator(ComponentConfigDispatcher):
    """Dispatch sink configuration to its registered validator."""

    def __init__(self, registry: ComponentRegistry[Any]) -> None:
        """Initialize the sink validator registry."""
        super().__init__(registry, component_kind="sink")
