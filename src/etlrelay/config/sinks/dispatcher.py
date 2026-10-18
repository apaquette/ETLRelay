"""Sink-specific dispatch for component configuration validation.

This module provides a sink configuration validator that delegates to the
shared component dispatcher using the sink component registry.
"""

from typing import Any

from etlrelay.config.component_dispatcher import ComponentConfigDispatcher
from etlrelay.config.registry import ComponentRegistry


class SinkConfigValidator(ComponentConfigDispatcher):
    """Dispatch sink configuration to its registered validator.

    This class specializes the shared component dispatcher for sink
    configurations. It resolves each configuration's ``type`` against
    the supplied registry and delegates validation to the corresponding
    registered validator.
    """

    def __init__(self, registry: ComponentRegistry[Any]) -> None:
        """Initialize the validator with the sink component registry.

        Args:
            registry: Registry containing sink registrations and their
                configuration validators.
        """
        super().__init__(registry, component_kind="sink")
