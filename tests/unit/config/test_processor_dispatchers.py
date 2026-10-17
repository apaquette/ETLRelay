"""Unit tests for processor configuration dispatch."""

from collections.abc import Callable, Mapping
from unittest.mock import Mock

import pytest

from etlrelay.config.component_validator import ComponentConfigValidator
from etlrelay.config.processors.dispatcher import ProcessorConfigValidator
from etlrelay.config.processors.sequence import ProcessorSequenceConfigValidator
from etlrelay.config.registry import ComponentRegistration, ComponentRegistry


class StubConfigValidator:
    """Record validation calls and return configured errors."""

    def __init__(self, errors: list[str] | None = None) -> None:
        self.errors = errors if errors is not None else []
        self.calls: list[tuple[object, str]] = []

    def validate(self, config: object, path: str) -> list[str]:
        self.calls.append((config, path))
        return self.errors


def make_registry(
    validators: Mapping[str, ComponentConfigValidator],
    factories: Mapping[
        str, Callable[[Mapping[str, object]], object]
    ] | None = None,
) -> ComponentRegistry[object]:
    """Create a processor registry using test doubles."""
    supplied_factories = factories or {}

    return ComponentRegistry(
        {
            name: ComponentRegistration[object](
                validator=validator,
                factory=supplied_factories.get(
                    name,
                    Mock(return_value=object()),
                ),
            )
            for name, validator in validators.items()
        }
    )


def test_processor_dispatcher_delegates_to_registered_validator() -> None:
    validator = StubConfigValidator()
    config = {"type": "select_columns", "columns": ["id"]}
    dispatcher = ProcessorConfigValidator(
        make_registry({"select_columns": validator})
    )

    errors = dispatcher.validate(config, "processors[0]")

    assert errors == []
    assert validator.calls == [(config, "processors[0]")]


def test_processor_dispatcher_returns_child_validation_errors() -> None:
    validator = StubConfigValidator(["invalid processor configuration"])
    dispatcher = ProcessorConfigValidator(
        make_registry({"select_columns": validator})
    )

    errors = dispatcher.validate(
        {"type": "select_columns"},
        "processors[0]",
    )

    assert errors == ["invalid processor configuration"]


def test_processor_dispatcher_rejects_missing_type() -> None:
    validator = StubConfigValidator()
    dispatcher = ProcessorConfigValidator(
        make_registry({"select_columns": validator})
    )

    errors = dispatcher.validate({}, "processors[0]")

    assert any("processors[0].type" in error for error in errors)
    assert validator.calls == []


def test_processor_dispatcher_rejects_unregistered_type() -> None:
    validator = StubConfigValidator()
    dispatcher = ProcessorConfigValidator(
        make_registry({"select_columns": validator})
    )

    errors = dispatcher.validate(
        {"type": "unknown_processor"},
        "processors[0]",
    )

    assert any("processors[0].type" in error for error in errors)
    assert validator.calls == []


def test_processor_dispatcher_does_not_invoke_factory() -> None:
    validator = StubConfigValidator()
    factory = Mock(return_value=object())
    dispatcher = ProcessorConfigValidator(
        make_registry(
            {"select_columns": validator},
            {"select_columns": factory},
        )
    )

    dispatcher.validate(
        {"type": "select_columns"},
        "processors[0]",
    )

    factory.assert_not_called()


def test_processor_sequence_accepts_empty_list() -> None:
    validator = StubConfigValidator()
    sequence_validator = ProcessorSequenceConfigValidator(
        ProcessorConfigValidator(
            make_registry({"select_columns": validator})
        )
    )

    assert sequence_validator.validate([], "processors") == []
    assert validator.calls == []


@pytest.mark.parametrize("config", [None, {}, "processors", ("item",)])
def test_processor_sequence_rejects_non_list_config(
    config: object,
) -> None:
    validator = StubConfigValidator()
    sequence_validator = ProcessorSequenceConfigValidator(
        ProcessorConfigValidator(
            make_registry({"select_columns": validator})
        )
    )

    errors = sequence_validator.validate(config, "processors")

    assert any("processors" in error and "list" in error for error in errors)
    assert validator.calls == []


def test_processor_sequence_delegates_in_order_with_indexed_paths() -> None:
    select_validator = StubConfigValidator()
    rename_validator = StubConfigValidator()
    sequence_validator = ProcessorSequenceConfigValidator(
        ProcessorConfigValidator(
            make_registry(
                {
                    "select_columns": select_validator,
                    "rename_columns": rename_validator,
                }
            )
        )
    )
    first = {"type": "select_columns", "columns": ["id"]}
    second = {"type": "rename_columns", "columns": {"id": "identifier"}}

    errors = sequence_validator.validate([first, second], "processors")

    assert errors == []
    assert select_validator.calls == [(first, "processors[0]")]
    assert rename_validator.calls == [(second, "processors[1]")]


def test_processor_sequence_aggregates_errors_and_continues() -> None:
    select_validator = StubConfigValidator(["invalid selection"])
    rename_validator = StubConfigValidator(["invalid rename"])
    sequence_validator = ProcessorSequenceConfigValidator(
        ProcessorConfigValidator(
            make_registry(
                {
                    "select_columns": select_validator,
                    "rename_columns": rename_validator,
                }
            )
        )
    )

    errors = sequence_validator.validate(
        [
            {"type": "select_columns"},
            {"type": "rename_columns"},
        ],
        "processors",
    )

    assert errors == ["invalid selection", "invalid rename"]
    assert len(select_validator.calls) == 1
    assert len(rename_validator.calls) == 1


def test_processor_sequence_reports_invalid_item_at_its_index() -> None:
    validator = StubConfigValidator()
    sequence_validator = ProcessorSequenceConfigValidator(
        ProcessorConfigValidator(
            make_registry({"select_columns": validator})
        )
    )

    errors = sequence_validator.validate(
        [{"type": "select_columns"}, 42],
        "processors",
    )

    assert errors == ["processors[1] must be a mapping."]
    assert validator.calls == [
        ({"type": "select_columns"}, "processors[0]")
    ]