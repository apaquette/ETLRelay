"""Protocol for constructing runtime components from validated configuration."""

from collections.abc import Mapping
from typing import Protocol, TypeVar

ComponentT_co = TypeVar("ComponentT_co", covariant=True)


class ComponentFactory(Protocol[ComponentT_co]):
    """Construct a runtime component from validated configuration."""

    def build(self, config: Mapping[str, object]) -> ComponentT_co:
        """Build and return a runtime component."""
        ...
