"""Dispatcher for processor configuration validation."""

from typing import Any

from etlrelay.config.component_dispatcher import ComponentConfigDispatcher
from etlrelay.config.registry import ComponentRegistry


class ProcessorConfigValidator(ComponentConfigDispatcher):
    """Dispatch processor configuration to its registered validator."""

    def __init__(self, registry: ComponentRegistry[Any]) -> None:
        """Initialize the processor validator registry."""
        super().__init__(registry, component_kind="processor")