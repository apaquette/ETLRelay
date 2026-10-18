"""Unit tests for class-based FilterRows construction."""

from collections.abc import Mapping
from unittest.mock import patch

from etlrelay.config.processors import FilterRowsConfigFactory


def test_build_constructs_processor_with_predicate_properties() -> None:
    config: Mapping[str, object] = {
        "type": "filter_rows",
        "column": "amount",
        "operator": ">=",
        "value": 0,
    }

    with patch("etlrelay.config.processors.filter_rows.FilterRows") as constructor:
        result = FilterRowsConfigFactory().build(config)

    constructor.assert_called_once_with(
        column="amount",
        operator=">=",
        value=0,
    )
    assert result is constructor.return_value


def test_build_does_not_mutate_configuration() -> None:
    config: Mapping[str, object] = {
        "type": "filter_rows",
        "column": "status",
        "operator": "==",
        "value": "ready",
    }
    original = dict(config)

    with patch("etlrelay.config.processors.filter_rows.FilterRows"):
        FilterRowsConfigFactory().build(config)

    assert config == original
