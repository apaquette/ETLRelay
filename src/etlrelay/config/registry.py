from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypeVar

from etlrelay.config.component_validator import ComponentConfigValidator

T = TypeVar("T")


@dataclass(frozen=True)
class ComponentRegistration[T]:
    """Associate a component configuration validator with its factory.

    A registration defines how a component's configuration is validated and
    how its runtime implementation is constructed.

    Attributes:
        validator: Validator used to check the component's configuration.
        factory: Callable that constructs the runtime component from its
            configuration mapping.

    Factories are stored without being invoked. Their invocation is the
    responsibility of the component builder.
    """

    validator: ComponentConfigValidator
    factory: Callable[[Mapping[str, object]], T]


class ComponentRegistry[T]:
    """Provide read-only lookup of named component registrations.

    The registry copies the supplied mapping during initialization, preventing
    subsequent changes to the original mapping from affecting its contents.
    Registration names must not be empty or contain only whitespace.

    Attributes:
        _registration: Mapping of component names to their registrations.
    """

    def __init__(self, registration: Mapping[str, ComponentRegistration[T]]) -> None:
        """Initialize the registry from a mapping of names to registrations.

        Args:
            registration: Mapping of component names to their registrations.

        Raises:
            ValueError: If any registration name is empty or contains only
                whitespace.
        """
        for key in registration.keys():
            if not key.strip():
                raise ValueError("Key name must be valid strings")
        self._registration = dict(registration)

    def get(self, name: str) -> ComponentRegistration[T]:
        """Return the registration associated with a component name.

        Args:
            name: Name of the component registration to retrieve.

        Returns:
            The registration associated with ``name``.

        Raises:
            KeyError: If ``name`` is not registered.
        """
        if name not in self.names():
            raise KeyError(f"No match in registry for name: {name}")
        return self._registration[name]

    def names(self) -> tuple[str, ...]:
        """Return the registered component names in insertion order.

        Returns:
            A tuple containing the names of all registered components.
        """
        return tuple(self._registration)
