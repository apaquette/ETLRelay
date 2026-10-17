"""Unit tests for root configuration validation."""

from unittest.mock import Mock

import pytest

from etlrelay.config.errors import ConfigurationError
from etlrelay.config.validator import ConfigValidator


def valid_config() -> dict[str, object]:
    """Return a minimal version-one pipeline configuration."""
    return {
        "version": 1,
        "source": {"type": "file"},
        "processors": [],
        "sink": {"type": "file"},
    }


def make_validator() -> tuple[ConfigValidator, Mock, Mock, Mock]:
    """Create a root validator with independent child validators."""
    source = Mock()
    processors = Mock()
    sink = Mock()

    source.validate.return_value = []
    processors.validate.return_value = []
    sink.validate.return_value = []

    return (
        ConfigValidator(
            source_validator=source,
            processor_validator=processors,
            sink_validator=sink,
        ),
        source,
        processors,
        sink,
    )


def test_valid_config_delegates_to_all_component_validators() -> None:
    config = valid_config()
    validator, source, processors, sink = make_validator()

    validator.validate(config)

    source.validate.assert_called_once_with(config["source"], "source")
    processors.validate.assert_called_once_with(
        config["processors"],
        "processors",
    )
    sink.validate.assert_called_once_with(config["sink"], "sink")


def test_empty_processor_list_is_valid() -> None:
    config = valid_config()
    config["processors"] = []
    validator, _, processors, _ = make_validator()

    validator.validate(config)

    processors.validate.assert_called_once_with([], "processors")


def test_non_mapping_root_raises_configuration_error() -> None:
    validator, source, processors, sink = make_validator()

    with pytest.raises(ConfigurationError):
        validator.validate(None)

    source.validate.assert_not_called()
    processors.validate.assert_not_called()
    sink.validate.assert_not_called()


def test_missing_required_top_level_fields_raise_error() -> None:
    validator, _, _, _ = make_validator()

    with pytest.raises(ConfigurationError) as exc_info:
        validator.validate({})

    message = str(exc_info.value)
    for field in ("version", "source", "processors", "sink"):
        assert field in message


@pytest.mark.parametrize("version", [0, 2, "1", True, None])
def test_unsupported_or_invalid_version_raises_error(
    version: object,
) -> None:
    config = valid_config()
    config["version"] = version
    validator, _, _, _ = make_validator()

    with pytest.raises(ConfigurationError) as exc_info:
        validator.validate(config)

    assert "version" in str(exc_info.value)


def test_unknown_top_level_field_raises_error() -> None:
    config = valid_config()
    config["unexpected"] = True
    validator, _, _, _ = make_validator()

    with pytest.raises(ConfigurationError) as exc_info:
        validator.validate(config)

    assert "unexpected" in str(exc_info.value)


def test_component_errors_are_aggregated() -> None:
    config = valid_config()
    validator, source, processors, sink = make_validator()
    source.validate.return_value = ["invalid source"]
    processors.validate.return_value = ["invalid processor"]
    sink.validate.return_value = ["invalid sink"]

    with pytest.raises(ConfigurationError) as exc_info:
        validator.validate(config)

    message = str(exc_info.value)
    assert "invalid source" in message
    assert "invalid processor" in message
    assert "invalid sink" in message

    source.validate.assert_called_once()
    processors.validate.assert_called_once()
    sink.validate.assert_called_once()


def test_invalid_top_level_key_type_is_rejected() -> None:
    config = valid_config()
    config[42] = "unexpected"  # type: ignore[dict-item]
    validator, source, processors, sink = make_validator()

    with pytest.raises(ConfigurationError):
        validator.validate(config)

    source.validate.assert_not_called()
    processors.validate.assert_not_called()
    sink.validate.assert_not_called()
