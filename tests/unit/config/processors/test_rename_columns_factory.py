"""Unit tests for class-based RenameColumns construction."""

from collections.abc import Mapping
from unittest.mock import patch

from etlrelay.config.processors import RenameColumnsConfigFactory


def test_build_constructs_processor_with_configured_mapping() -> None:
    mapping = {"id": "record_id", "amount": "total"}
    config: Mapping[str, object] = {
        "type": "rename_columns",
        "mapping": mapping,
    }

    with patch("etlrelay.config.processors.rename_columns.RenameColumns") as constructor:
        result = RenameColumnsConfigFactory().build(config)

    constructor.assert_called_once_with(mapping=mapping)
    assert result is constructor.return_value


def test_build_does_not_mutate_configuration() -> None:
    mapping = {"id": "record_id"}
    config: Mapping[str, object] = {
        "type": "rename_columns",
        "mapping": mapping,
    }
    original = {"type": "rename_columns", "mapping": dict(mapping)}

    with patch("etlrelay.config.processors.rename_columns.RenameColumns"):
        RenameColumnsConfigFactory().build(config)

    assert config == original
