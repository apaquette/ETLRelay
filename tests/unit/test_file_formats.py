"""Unit tests for the tabular file-format registry."""

from collections.abc import Callable
from unittest.mock import Mock

import pytest

from etlrelay.file_formats import TabularFileFormatRegistry


def make_registry() -> TabularFileFormatRegistry:
    """Create a registry with independent reader and writer factories."""
    csv_reader = Mock(return_value="csv-reader")
    parquet_reader = Mock(return_value="parquet-reader")
    csv_writer = Mock(return_value="csv-writer")
    parquet_writer = Mock(return_value="parquet-writer")

    return TabularFileFormatRegistry(
        readers={
            "csv": csv_reader,
            "parquet": parquet_reader,
        },
        writers={
            "csv": csv_writer,
            "parquet": parquet_writer,
        },
    )


def test_supports_registered_reading_formats() -> None:
    registry = make_registry()

    assert registry.supports_reading("csv")
    assert registry.supports_reading("parquet")


def test_supports_registered_writing_formats() -> None:
    registry = make_registry()

    assert registry.supports_writing("csv")
    assert registry.supports_writing("parquet")


def test_reading_and_writing_support_are_independent() -> None:
    registry = TabularFileFormatRegistry(
        readers={"csv": Mock(return_value="csv-reader")},
        writers={"parquet": Mock(return_value="parquet-writer")},
    )

    assert registry.supports_reading("csv")
    assert not registry.supports_writing("csv")
    assert registry.supports_writing("parquet")
    assert not registry.supports_reading("parquet")


def test_readable_formats_returns_names_in_insertion_order() -> None:
    registry = make_registry()

    assert registry.readable_formats() == ("csv", "parquet")


def test_writable_formats_returns_names_in_insertion_order() -> None:
    registry = make_registry()

    assert registry.writable_formats() == ("csv", "parquet")


def test_create_reader_invokes_registered_factory() -> None:
    factory = Mock(return_value="csv-reader")
    registry = TabularFileFormatRegistry(
        readers={"csv": factory},
        writers={},
    )

    assert registry.create_reader("csv") == "csv-reader"
    factory.assert_called_once_with()


def test_create_writer_invokes_registered_factory() -> None:
    factory = Mock(return_value="csv-writer")
    registry = TabularFileFormatRegistry(
        readers={},
        writers={"csv": factory},
    )

    assert registry.create_writer("csv") == "csv-writer"
    factory.assert_called_once_with()


def test_construction_and_capability_checks_do_not_invoke_factories() -> None:
    reader_factory = Mock(return_value="csv-reader")
    writer_factory = Mock(return_value="csv-writer")

    registry = TabularFileFormatRegistry(
        readers={"csv": reader_factory},
        writers={"csv": writer_factory},
    )

    assert registry.supports_reading("csv")
    assert registry.supports_writing("csv")
    assert registry.readable_formats() == ("csv",)
    assert registry.writable_formats() == ("csv",)

    reader_factory.assert_not_called()
    writer_factory.assert_not_called()


@pytest.mark.parametrize("name", ["unknown", ""])
def test_create_reader_rejects_unregistered_format(name: str) -> None:
    registry = make_registry()

    with pytest.raises(KeyError):
        registry.create_reader(name)


@pytest.mark.parametrize("name", ["unknown", ""])
def test_create_writer_rejects_unregistered_format(name: str) -> None:
    registry = make_registry()

    with pytest.raises(KeyError):
        registry.create_writer(name)


def test_registry_copies_input_mappings() -> None:
    reader_factory = Mock(return_value="csv-reader")
    writer_factory = Mock(return_value="csv-writer")
    readers: dict[str, Callable[[], object]] = {"csv": reader_factory}
    writers: dict[str, Callable[[], object]] = {"csv": writer_factory}

    registry = TabularFileFormatRegistry(
        readers=readers,
        writers=writers,
    )

    readers["parquet"] = Mock(return_value="parquet-reader")
    writers.clear()

    assert registry.readable_formats() == ("csv",)
    assert registry.writable_formats() == ("csv",)
    assert registry.create_writer("csv") == "csv-writer"
