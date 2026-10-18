"""Protocol defining the interface for component configuration validators.

Component configuration validators implement this interface to validate
component-specific configuration and return descriptive error messages.
"""

from typing import Any, Protocol


class ComponentConfigValidator(Protocol):
    """Define the interface for validating component configuration.

    Implementations validate configuration for a particular component type
    and report validation failures as error messages rather than returning
    a boolean status.
    """

    def validate(self, config: Any, path: str) -> list[str]:
        """Validate component-specific configuration.

        Args:
            config: Configuration value to validate.
            path: Configuration path identifying the location being validated.
                Implementations use this path to contextualize error messages.

        Returns:
            A list of validation error messages. An empty list indicates that
            validation succeeded.

        Note:
            The specific validation rules depend on the implementation.
        """
        ...
