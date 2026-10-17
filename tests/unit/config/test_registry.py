"""Tests for registrations using class-based component factories."""

from collections.abc import Mapping
from dataclasses import FrozenInstanceError

import pytest

from etlrelay.config.component_validator import ComponentConfigValidator
from etlrelay.config.registry import ComponentRegistration, ComponentRegistry


class StubConfigValidator:
    """Minimal validator implementation for registry unit tests."""

    def validate(self, config: object, path: str) -> list[str]:
        return []


class StubConfigFactory:
    """Factory spy implementing the proposed build(config) interface."""

    def __init__(self, result: str = "constructed") -> None:
        self.result = result
        self.configs: list[Mapping[str, object]] = []

    def build(self, config: Mapping[str, object]) -> str:
        self.configs.append(config)
        return self.result


def make_registration(
    validator: ComponentConfigValidator | None = None,
    factory: StubConfigFactory | None = None,
) -> ComponentRegistration[str]:
    return ComponentRegistration(
        validator=validator or StubConfigValidator(),
        factory=factory or StubConfigFactory(),
    )


def test_registration_keeps_validator_and_factory_associated() -> None:
    validator = StubConfigValidator()
    factory = StubConfigFactory()

    registration = ComponentRegistration[str](validator=validator, factory=factory)

    assert registration.validator is validator
    assert registration.factory is factory
    assert factory.configs == []


def test_registration_is_immutable() -> None:
    registration = make_registration()

    with pytest.raises(FrozenInstanceError):
        registration.factory = StubConfigFactory()


def test_registry_returns_registered_component() -> None:
    registration = make_registration()
    registry = ComponentRegistry[str]({"file": registration})

    assert registry.get("file") is registration


def test_registry_names_returns_registered_names_in_insertion_order() -> None:
    file_registration = make_registration()
    sql_registration = make_registration()
    registry = ComponentRegistry[str]({"file": file_registration, "sql": sql_registration})

    assert registry.names() == ("file", "sql")


def test_registry_names_returns_a_tuple() -> None:
    registry = ComponentRegistry[str]({"file": make_registration()})

    names = registry.names()

    assert isinstance(names, tuple)
    assert names == ("file",)


def test_registry_raises_key_error_for_unknown_name() -> None:
    registry = ComponentRegistry[str]({"file": make_registration()})

    with pytest.raises(KeyError, match="unknown"):
        registry.get("unknown")


def test_registry_copies_input_mapping() -> None:
    registration = make_registration()
    registrations = {"file": registration}
    registry = ComponentRegistry[str](registrations)

    registrations["sql"] = make_registration()
    del registrations["file"]

    assert registry.names() == ("file",)
    assert registry.get("file") is registration
    with pytest.raises(KeyError):
        registry.get("sql")


def test_registry_does_not_invoke_factories_during_construction_or_lookup() -> None:
    factory = StubConfigFactory()
    registration = make_registration(factory=factory)

    registry = ComponentRegistry[str]({"file": registration})
    retrieved = registry.get("file")
    names = registry.names()

    assert retrieved is registration
    assert names == ("file",)
    assert factory.configs == []


def test_registered_factory_can_be_invoked_explicitly() -> None:
    factory = StubConfigFactory()
    registration = make_registration(factory=factory)
    registry = ComponentRegistry[str]({"file": registration})
    config: Mapping[str, object] = {"type": "file", "path": "input.csv"}

    result = registry.get("file").factory.build(config)

    assert result == "constructed"
    assert factory.configs == [config]


@pytest.mark.parametrize("name", ["", " ", "\t"])
def test_registry_rejects_empty_or_whitespace_names(name: str) -> None:
    with pytest.raises(ValueError, match="name"):
        ComponentRegistry[str]({name: make_registration()})


def test_registry_allows_an_empty_registry() -> None:
    registry = ComponentRegistry[str]({})

    assert registry.names() == ()
    with pytest.raises(KeyError):
        registry.get("file")
