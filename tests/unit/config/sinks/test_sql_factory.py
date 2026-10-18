"""Unit tests for SQL sink component construction."""

from unittest.mock import Mock

from sqlalchemy.engine import Engine

from etlrelay.config.sinks.sql import SqlSinkConfigFactory
from etlrelay.sinks.sql import SqlSink


def test_build_constructs_sql_sink_with_configured_arguments(monkeypatch) -> None:
    engine = Mock(spec=Engine)
    engine_factory = Mock()
    engine_factory.create.return_value = engine
    sink_constructor = Mock(spec=SqlSink)
    monkeypatch.setattr("etlrelay.config.sinks.sql.SqlSink", sink_constructor)
    factory = SqlSinkConfigFactory(engine_factory=engine_factory)
    config = {
        "type": "sql",
        "connection_url_env": "SINK_DATABASE_URL",
        "table_name": "processed_records",
        "schema": "analytics",
    }

    result = factory.build(config)

    engine_factory.create.assert_called_once_with("SINK_DATABASE_URL")
    sink_constructor.assert_called_once_with(
        engine=engine,
        table_name="processed_records",
        schema="analytics",
    )
    assert result is sink_constructor.return_value


def test_build_passes_none_when_schema_is_omitted(monkeypatch) -> None:
    engine = Mock(spec=Engine)
    engine_factory = Mock()
    engine_factory.create.return_value = engine
    sink_constructor = Mock(spec=SqlSink)
    monkeypatch.setattr("etlrelay.config.sinks.sql.SqlSink", sink_constructor)
    factory = SqlSinkConfigFactory(engine_factory=engine_factory)

    factory.build(
        {
            "type": "sql",
            "connection_url_env": "SINK_DATABASE_URL",
            "table_name": "processed_records",
        }
    )

    sink_constructor.assert_called_once_with(
        engine=engine,
        table_name="processed_records",
        schema=None,
    )
