"""Unit tests for SQL source component construction."""

from unittest.mock import Mock

from sqlalchemy.engine import Engine

from etlrelay.config.sources.sql import SqlSourceConfigFactory
from etlrelay.sources.sql import SqlSource


def test_build_constructs_sql_source_with_configured_arguments(
    monkeypatch,
) -> None:
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
    }

    result = factory.build(config)

    engine_factory.create.assert_called_once_with("SOURCE_DATABASE_URL")
    source_constructor.assert_called_once_with(
        engine=engine,
        query="SELECT id FROM records WHERE state = :state",
        parameters={"state": "ready"},
    )
    assert result is source_constructor.return_value


def test_build_passes_none_when_parameters_are_omitted(monkeypatch) -> None:
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
    )
