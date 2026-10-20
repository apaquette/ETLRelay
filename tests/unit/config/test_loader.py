import logging
from io import BytesIO
from unittest.mock import Mock

import pytest

from etlrelay.config.loader import ConfigLoader


def test_load_opens_stream_reads_validates_and_returns_mapping() -> None:
    config = {
        "version": 1,
        "source": {"type": "file"},
        "processors": [],
        "sink": {"type": "file"},
    }
    stream = BytesIO(b"configuration content")
    filesystem = Mock()
    filesystem.open_read.return_value = stream

    reader = Mock()
    reader.read.return_value = config

    validator = Mock()
    loader = ConfigLoader(filesystem, reader, validator)

    result = loader.load("pipeline.yml")

    filesystem.open_read.assert_called_once_with("pipeline.yml")
    reader.read.assert_called_once_with(stream)
    validator.validate.assert_called_once_with(config)

    assert result is config
    assert stream.closed


def test_load_closes_stream_when_reader_fails() -> None:
    stream = BytesIO(b"invalid configuration content")
    filesystem = Mock()
    filesystem.open_read.return_value = stream

    reader = Mock()
    reader.read.side_effect = ValueError("invalid document")

    validator = Mock()
    loader = ConfigLoader(filesystem, reader, validator)

    with pytest.raises(ValueError, match="invalid document"):
        loader.load("pipeline.yml")

    assert stream.closed
    validator.validate.assert_not_called()


def test_load_logs_configuration_lifecycle(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Log configuration loading and successful validation."""
    config = {
        "version": 1,
        "source": {"type": "file"},
        "processors": [],
        "sink": {"type": "file"},
    }

    sensitive_path = "private-customer-pipeline.yaml"

    filesystem = Mock()
    filesystem.open_read.return_value = BytesIO(b"configuration")

    reader = Mock()
    reader.read.return_value = config

    validator = Mock()

    loader = ConfigLoader(filesystem, reader, validator)

    with caplog.at_level(logging.DEBUG, logger="etlrelay.config.loader"):
        result = loader.load(sensitive_path)

    messages = [
        record.message for record in caplog.records if record.name == "etlrelay.config.loader"
    ]

    assert messages == [
        "Configuration loading started.",
        "Configuration validation completed.",
    ]

    assert sensitive_path not in caplog.text
    assert result is config

    validator.validate.assert_called_once_with(config)


def test_validation_failure_does_not_log_success(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Preserve validation errors without logging configuration contents."""
    secret = "private-configuration-value"
    original_error = ValueError(f"Invalid configuration: {secret}")

    filesystem = Mock()
    filesystem.open_read.return_value = BytesIO(b"configuration")

    reader = Mock()
    reader.read.return_value = {"version": 1}

    validator = Mock()
    validator.validate.side_effect = original_error

    loader = ConfigLoader(filesystem, reader, validator)

    with caplog.at_level(logging.DEBUG, logger="etlrelay.config.loader"):
        with pytest.raises(ValueError) as exc_info:
            loader.load("pipeline.yaml")

    assert exc_info.value is original_error

    messages = [
        record.message for record in caplog.records if record.name == "etlrelay.config.loader"
    ]

    assert messages == ["Configuration loading started."]
    assert secret not in caplog.text
