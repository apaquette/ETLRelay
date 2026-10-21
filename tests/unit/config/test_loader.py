import logging
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from unittest.mock import Mock

import pytest

from etlrelay.config.loader import ConfigLoader
from etlrelay.core import KeyValueReader
from etlrelay.default_components import create_default_component_catalog
from etlrelay.security import PathValidator
from etlrelay.storage import LocalFileSystem


def test_load_accepts_a_non_yaml_key_value_reader(tmp_path: Path) -> None:
    """Document parsing is substitutable independently of schema validation."""
    config: Mapping[str, object] = {
        "version": 1,
        "source": {
            "type": "file",
            "path": "input.csv",
            "format": "csv",
            "storage": {"type": "local"},
        },
        "processors": [],
        "sink": {
            "type": "file",
            "path": "output.csv",
            "format": "csv",
            "storage": {"type": "local"},
        },
    }
    document = b"This is deliberately not a YAML mapping."
    (tmp_path / "pipeline.custom").write_bytes(document)

    class MappingReader:
        stream: BinaryIO | None = None

        def read(self, stream: BinaryIO) -> Mapping[str, object]:
            self.stream = stream
            assert stream.read() == document
            return config

    reader = MappingReader()
    protocol_reader: KeyValueReader = reader
    loader = ConfigLoader(
        LocalFileSystem(PathValidator(tmp_path)),
        protocol_reader,
        create_default_component_catalog().config_validator,
    )

    assert loader.load("pipeline.custom") is config
    assert reader.stream is not None and reader.stream.closed


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
