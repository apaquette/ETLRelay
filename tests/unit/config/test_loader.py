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
