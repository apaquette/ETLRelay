from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ComponentConfigValidator(Protocol):
    def validate(self, config: Any, path: str) -> list[str]: ...
