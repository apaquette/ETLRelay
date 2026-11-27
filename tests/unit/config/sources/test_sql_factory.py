"""Unit tests for SQL source component construction."""

from unittest.mock import Mock

import pyarrow as pa
import pytest
from sqlalchemy.engine import Engine

from etlrelay.config.sources.sql import SqlSourceConfigFactory
from etlrelay.sources.sql import SqlSource


def test_build_constructs_sql_source_with_configured_arguments(monkeypatch) -> None:
    engine = Mock(spec=Engine)
    engine_factory = Mock()
    engine_factory.create.return_value = engine
    source_constructor = Mock(spec=SqlSource)
    monkeypatch.setattr("etlrelay.config.sources.sql.SqlSource", source_constructor)
    factory = SqlSourceConfigFactory(engine_factory=engine_factory)
    config = {
        "type": "sql",
        "connection_url_env": "SOURCE_DATABASE_URL",
        "query": "SELECT id FROM records WHERE state = :state",
        "parameters": {"state": "ready"},
        "batch_size": 10,
        "schema": {
            "fields": [
                {"name": "id", "type": "int64", "nullable": False},
            ]
        },
    }

    result = factory.build(config)

    engine_factory.create.assert_called_once_with("SOURCE_DATABASE_URL")
    source_constructor.assert_called_once_with(
        engine=engine,
        query="SELECT id FROM records WHERE state = :state",
        parameters={"state": "ready"},
        batch_size=10,
        schema=pa.schema([pa.field("id", pa.int64(), nullable=False)]),
    )
    assert result is source_constructor.return_value


def test_build_passes_none_for_omitted_optional_source_settings(monkeypatch) -> None:
    engine = Mock(spec=Engine)
    engine_factory = Mock()
    engine_factory.create.return_value = engine
    source_constructor = Mock(spec=SqlSource)
    monkeypatch.setattr("etlrelay.config.sources.sql.SqlSource", source_constructor)
    factory = SqlSourceConfigFactory(engine_factory=engine_factory)

    factory.build(
        {
            "type": "sql",
            "connection_url_env": "SOURCE_DATABASE_URL",
            "query": "SELECT id FROM records",
        }
    )

    source_constructor.assert_called_once_with(
        engine=engine,
        query="SELECT id FROM records",
        parameters=None,
        batch_size=None,
        schema=None,
    )



def test_build_rejects_invalid_yaml_source_before_creating_engine() -> None:
    engine_factory = Mock()
    factory = SqlSourceConfigFactory(engine_factory=engine_factory)

    with pytest.raises(ValueError, match="source.batch_size"):
        factory.build(
            {
                "type": "sql",
                "connection_url_env": "SOURCE_DATABASE_URL",
                "query": "SELECT id FROM records",
                "batch_size": 0,
            }
        )

    engine_factory.create.assert_not_called()
