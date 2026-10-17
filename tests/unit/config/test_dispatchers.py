"""Unit tests for component configuration dispatchers."""

from collections.abc import Mapping
from typing import Any
from unittest.mock import Mock

import pytest

from etlrelay.config.component_validator import ComponentConfigValidator
from etlrelay.config.registry import ComponentRegistration, ComponentRegistry
from etlrelay.config.sinks.dispatcher import SinkConfigValidator
from etlrelay.config.sources.dispatcher import SourceConfigValidator
from etlrelay.config.storage.dispatcher import StorageConfigValidator


class StubConfigValidator:
    """Record calls and return configured validation errors."""

    def __init__(self, errors: list[str] | None = None) -> None:
        self.errors = errors if errors is not None else []
        self.calls: list[tuple[object, str]] = []

    def validate(self, config: object, path: str) -> list[str]:
        self.calls.append((config, path))
        return self.errors


def build_component(config: Mapping[str, object]) -> str:
    """Return a marker without constructing an actual component."""
    return str(config.get("type", "component"))


def make_registry(
    validators: Mapping[str, ComponentConfigValidator],
    factories: Mapping[str, Any] | None = None,
) -> ComponentRegistry[str]:
    """Create a registry with validators and inert test factories."""
    factories = factories or {}

    return ComponentRegistry(
        {
            name: ComponentRegistration[str](
                validator=validator,
                factory=factories.get(name, build_component),
            )
            for name, validator in validators.items()
        }
    )


DISPATCHERS = [
    (StorageConfigValidator, "local", "source.storage"),
    (SourceConfigValidator, "file", "source"),
    (SinkConfigValidator, "file", "sink"),
]


@pytest.mark.parametrize(
    ("dispatcher_class", "component_type", "path"),
    DISPATCHERS,
)
def test_dispatcher_delegates_to_registered_validator(
    dispatcher_class: type,
    component_type: str,
    path: str,
) -> None:
    child_validator = StubConfigValidator()
    registry = make_registry({component_type: child_validator})
    dispatcher = dispatcher_class(registry)
    config: dict[str, object] = {
        "type": component_type,
        "custom": "value",
    }

    errors = dispatcher.validate(config, path)

    assert errors == []
    assert child_validator.calls == [(config, path)]


@pytest.mark.parametrize(
    ("dispatcher_class", "component_type", "path"),
    DISPATCHERS,
)
def test_dispatcher_returns_errors_from_registered_validator(
    dispatcher_class: type,
    component_type: str,
    path: str,
) -> None:
    child_validator = StubConfigValidator(["invalid component configuration"])
    dispatcher = dispatcher_class(make_registry({component_type: child_validator}))

    errors = dispatcher.validate({"type": component_type}, path)

    assert errors == ["invalid component configuration"]


@pytest.mark.parametrize(
    ("dispatcher_class", "component_type", "path"),
    DISPATCHERS,
)
def test_dispatcher_rejects_non_mapping_configuration(
    dispatcher_class: type,
    component_type: str,
    path: str,
) -> None:
    child_validator = StubConfigValidator()
    dispatcher = dispatcher_class(make_registry({component_type: child_validator}))

    errors = dispatcher.validate(None, path)

    assert any("mapping" in error for error in errors)
    assert child_validator.calls == []


@pytest.mark.parametrize(
    ("dispatcher_class", "component_type", "path"),
    DISPATCHERS,
)
def test_dispatcher_rejects_missing_type(
    dispatcher_class: type,
    component_type: str,
    path: str,
) -> None:
    child_validator = StubConfigValidator()
    dispatcher = dispatcher_class(make_registry({component_type: child_validator}))

    errors = dispatcher.validate({"custom": "value"}, path)

    assert any(f"{path}.type" in error for error in errors)
    assert child_validator.calls == []


@pytest.mark.parametrize(
    ("dispatcher_class", "component_type", "path"),
    DISPATCHERS,
)
@pytest.mark.parametrize("invalid_type", ["", "  ", None, 42, []])
def test_dispatcher_rejects_invalid_type(
    dispatcher_class: type,
    component_type: str,
    path: str,
    invalid_type: object,
) -> None:
    child_validator = StubConfigValidator()
    dispatcher = dispatcher_class(make_registry({component_type: child_validator}))

    errors = dispatcher.validate({"type": invalid_type}, path)

    assert any(f"{path}.type" in error for error in errors)
    assert child_validator.calls == []


@pytest.mark.parametrize(
    ("dispatcher_class", "component_type", "path"),
    DISPATCHERS,
)
def test_dispatcher_rejects_unregistered_type(
    dispatcher_class: type,
    component_type: str,
    path: str,
) -> None:
    child_validator = StubConfigValidator()
    dispatcher = dispatcher_class(make_registry({component_type: child_validator}))

    errors = dispatcher.validate({"type": "unknown"}, path)

    assert any(f"{path}.type" in error for error in errors)
    assert any("registered" in error or "supported" in error for error in errors)
    assert child_validator.calls == []


@pytest.mark.parametrize(
    ("dispatcher_class", "component_type", "path"),
    DISPATCHERS,
)
def test_dispatcher_does_not_invoke_factory(
    dispatcher_class: type,
    component_type: str,
    path: str,
) -> None:
    child_validator = StubConfigValidator()
    factory = Mock(return_value="constructed")
    dispatcher = dispatcher_class(
        make_registry(
            {component_type: child_validator},
            factories={component_type: factory},
        )
    )

    dispatcher.validate({"type": component_type}, path)

    factory.assert_not_called()


@pytest.mark.parametrize(
    ("dispatcher_class", "component_type", "path"),
    DISPATCHERS,
)
def test_dispatcher_rejects_non_string_mapping_keys(
    dispatcher_class: type,
    component_type: str,
    path: str,
) -> None:
    child_validator = StubConfigValidator()
    dispatcher = dispatcher_class(make_registry({component_type: child_validator}))

    errors = dispatcher.validate(
        {"type": component_type, 42: "invalid key"},  # type: ignore[dict-item]
        path,
    )

    assert any("non-string key" in error for error in errors)
    assert child_validator.calls == []
