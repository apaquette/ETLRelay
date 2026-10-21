"""Unit tests for YamlReader's format-level contract.

These tests use in-memory streams. Filesystem composition belongs to
ConfigLoader tests and is not exercised here.
"""

import io
from collections.abc import Mapping
from io import BytesIO

import pytest
import yaml

from etlrelay.core import KeyValueReader
from etlrelay.readers import YamlReader


def test_yaml_reader_returns_a_mapping_with_nested_values() -> None:
    reader: KeyValueReader = YamlReader()
    stream = BytesIO(
        b"""\
name: example
settings:
  enabled: true
  retries: 3
columns: [id, amount]
"""
    )

    result = reader.read(stream)

    assert isinstance(result, Mapping)
    assert result == {
        "name": "example",
        "settings": {"enabled": True, "retries": 3},
        "columns": ["id", "amount"],
    }


def test_yaml_reader_requires_a_root_mapping() -> None:
    reader = YamlReader()

    for document in (b"null", b"42", b"- first\n- second\n", b"plain scalar"):
        stream = BytesIO(document)
        with pytest.raises(ValueError, match=r"(?i)(root|mapping)"):
            reader.read(stream)
        assert not stream.closed


def test_yaml_reader_rejects_non_string_root_keys() -> None:
    reader = YamlReader()
    stream = BytesIO(b"1: numeric key\n")

    with pytest.raises(ValueError, match=r"(?i)(key|string)"):
        reader.read(stream)
    assert not stream.closed


def test_yaml_reader_rejects_malformed_yaml() -> None:
    reader = YamlReader()
    stream = BytesIO(b"version: [1\nsource: {")

    with pytest.raises(yaml.YAMLError):
        reader.read(stream)
    assert not stream.closed


def test_yaml_reader_uses_safe_loading_and_rejects_python_object_tags() -> None:
    reader = YamlReader()
    stream = BytesIO(b"value: !!python/object/apply:os.system ['echo unsafe']")

    with pytest.raises(yaml.YAMLError):
        reader.read(stream)


@pytest.mark.parametrize(
    "document",
    [
        b"version: 1\nsource: first\nsource: second\n",
        b"source:\n  type: file\n  type: sql\n",
    ],
    ids=["root-key", "nested-key"],
)
def test_yaml_reader_rejects_duplicate_mapping_keys(document: bytes) -> None:
    reader = YamlReader()
    stream = BytesIO(document)

    with pytest.raises(yaml.YAMLError, match=r"(?i)duplicate|already defined|found.*key"):
        reader.read(stream)
    assert not stream.closed


def test_yaml_reader_rejects_multiple_documents() -> None:
    reader = YamlReader()
    stream = BytesIO(b"version: 1\n---\nversion: 1\n")

    with pytest.raises(yaml.YAMLError):
        reader.read(stream)
    assert not stream.closed


def test_yaml_reader_does_not_close_the_caller_owned_stream() -> None:
    reader = YamlReader()
    stream = BytesIO(b"version: 1\n")

    reader.read(stream)

    assert not stream.closed


def test_yaml_reader_propagates_stream_read_errors() -> None:
    class FailingStream:
        def read(self, *args: object, **kwargs: object) -> bytes:
            raise OSError("stream read failed")

    reader = YamlReader()

    with pytest.raises(OSError, match="stream read failed"):
        reader.read(FailingStream())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "yaml_content",
    [
        "? [one, two]\n: value\n",
        "nested:\n  ? [one, two]\n  : value\n",
    ],
    ids=["root-mapping-key", "nested-mapping-key"],
)
def test_yaml_reader_rejects_unhashable_mapping_keys(
    yaml_content: str,
) -> None:
    reader = YamlReader()
    stream = io.BytesIO(yaml_content.encode("utf-8"))

    with pytest.raises(yaml.YAMLError, match="unhashable key"):
        reader.read(stream)
