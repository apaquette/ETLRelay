from typing import Any, Protocol


class ComponentConfigValidator(Protocol):
    def validate(self, config: Any, path: str) -> list[str]: ...
