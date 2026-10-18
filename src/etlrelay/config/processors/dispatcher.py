"""Processor-specific dispatch for component configuration validation.

This module provides a processor configuration validator that delegates
configuration validation to the shared component dispatcher using the
processor registry.
"""

from typing import Any

from etlrelay.config.component_dispatcher import ComponentConfigDispatcher
from etlrelay.config.registry import ComponentRegistry


class ProcessorConfigValidator(ComponentConfigDispatcher):
    """Dispatch processor configuration to its registered validator.

    This class specializes the shared component dispatcher for processor
    configurations. It resolves each configuration's ``type`` against the
    supplied registry and delegates validation to the corresponding registered
    validator.
    """

    def __init__(self, registry: ComponentRegistry[Any]) -> None:
        """Initialize the validator with the processor component registry.

        Args:
            registry: Registry containing processor registrations and their
                configuration validators.
        """
        super().__init__(registry, component_kind="processor")
