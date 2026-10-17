"""Unit tests for class-based SelectColumns construction."""

from collections.abc import Mapping
from unittest.mock import patch

from etlrelay.config.processors import SelectColumnsConfigFactory


def test_build_constructs_processor_with_configured_columns() -> None:
    columns = ["id", "amount"]
    config: Mapping[str, object] = {
        "type": "select_columns",
        "columns": columns,
    }

    with patch("etlrelay.config.processors.select_columns.SelectColumns") as constructor:
        result = SelectColumnsConfigFactory().build(config)

    constructor.assert_called_once_with(columns=columns)
    assert result is constructor.return_value


def test_build_does_not_mutate_configuration() -> None:
    config: Mapping[str, object] = {
        "type": "select_columns",
        "columns": ["id", "amount"],
    }
    original = {"type": "select_columns", "columns": ["id", "amount"]}

    with patch("etlrelay.config.processors.select_columns.SelectColumns"):
        SelectColumnsConfigFactory().build(config)

    assert config == original
