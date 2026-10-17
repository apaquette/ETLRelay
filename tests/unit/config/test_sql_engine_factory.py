"""Unit tests for SQLAlchemy engine construction and ownership."""

from unittest.mock import Mock

import pytest
from sqlalchemy.engine import Engine

from etlrelay.config.sql_engine_factory import SqlEngineFactory, SqlEngineFactoryError

SOURCE_URL = "postgresql+psycopg://source_user:source_password@db/source"
SINK_URL = "postgresql+psycopg://sink_user:sink_password@db/sink"


def make_engine() -> Mock:
    return Mock(spec=Engine)


def test_preflight_resolves_urls_without_creating_engines() -> None:
    getenv = Mock(
        side_effect={
            "SOURCE_DATABASE_URL": SOURCE_URL,
            "SINK_DATABASE_URL": SINK_URL,
        }.get
    )
    engine_creator = Mock()
    factory = SqlEngineFactory(getenv=getenv, engine_creator=engine_creator)

    factory.preflight(
        {
            "source.connection_url_env": "SOURCE_DATABASE_URL",
            "sink.connection_url_env": "SINK_DATABASE_URL",
        }
    )

    getenv.assert_any_call("SOURCE_DATABASE_URL")
    getenv.assert_any_call("SINK_DATABASE_URL")
    engine_creator.assert_not_called()


def test_preflight_reports_all_missing_variables_without_exposing_urls() -> None:
    getenv = Mock(
        side_effect={
            "SOURCE_DATABASE_URL": SOURCE_URL,
            "SINK_DATABASE_URL": None,
        }.get
    )
    engine_creator = Mock()
    factory = SqlEngineFactory(getenv=getenv, engine_creator=engine_creator)

    with pytest.raises(SqlEngineFactoryError) as exc_info:
        factory.preflight(
            {
                "source.connection_url_env": "SOURCE_DATABASE_URL",
                "sink.connection_url_env": "SINK_DATABASE_URL",
            }
        )

    message = str(exc_info.value)
    assert "sink.connection_url_env" in message
    assert "SINK_DATABASE_URL" in message
    assert SOURCE_URL not in message
    assert "source_password" not in message
    engine_creator.assert_not_called()


def test_preflight_rejects_empty_environment_values() -> None:
    factory = SqlEngineFactory(
        getenv=lambda _name: "   ",
        engine_creator=Mock(),
    )

    with pytest.raises(SqlEngineFactoryError, match="SOURCE_DATABASE_URL"):
        factory.preflight({"source.connection_url_env": "SOURCE_DATABASE_URL"})


def test_preflight_reads_a_referenced_variable_once() -> None:
    getenv = Mock(return_value=SOURCE_URL)
    factory = SqlEngineFactory(getenv=getenv, engine_creator=Mock())

    factory.preflight(
        {
            "source.connection_url_env": "DATABASE_URL",
            "sink.connection_url_env": "DATABASE_URL",
        }
    )

    getenv.assert_called_once_with("DATABASE_URL")


def test_create_requires_successful_preflight() -> None:
    engine_creator = Mock()
    factory = SqlEngineFactory(getenv=lambda _name: SOURCE_URL, engine_creator=engine_creator)

    with pytest.raises(SqlEngineFactoryError, match="preflight"):
        factory.create("SOURCE_DATABASE_URL")

    engine_creator.assert_not_called()


def test_create_uses_resolved_url_and_tracks_engine() -> None:
    engine = make_engine()
    engine_creator = Mock(return_value=engine)
    factory = SqlEngineFactory(
        getenv=lambda _name: SOURCE_URL,
        engine_creator=engine_creator,
    )
    factory.preflight({"source.connection_url_env": "SOURCE_DATABASE_URL"})

    result = factory.create("SOURCE_DATABASE_URL")

    assert result is engine
    engine_creator.assert_called_once_with(SOURCE_URL)


def test_same_variable_reuses_engine() -> None:
    engine = make_engine()
    engine_creator = Mock(return_value=engine)
    factory = SqlEngineFactory(
        getenv=lambda _name: SOURCE_URL,
        engine_creator=engine_creator,
    )
    factory.preflight(
        {
            "source.connection_url_env": "DATABASE_URL",
            "sink.connection_url_env": "DATABASE_URL",
        }
    )

    source_engine = factory.create("DATABASE_URL")
    sink_engine = factory.create("DATABASE_URL")

    assert source_engine is sink_engine is engine
    engine_creator.assert_called_once_with(SOURCE_URL)


def test_close_disposes_each_created_engine_once() -> None:
    source_engine = make_engine()
    sink_engine = make_engine()
    engine_creator = Mock(side_effect=[source_engine, sink_engine])
    factory = SqlEngineFactory(
        getenv=lambda name: {
            "SOURCE_DATABASE_URL": SOURCE_URL,
            "SINK_DATABASE_URL": SINK_URL,
        }.get(name),
        engine_creator=engine_creator,
    )
    factory.preflight(
        {
            "source.connection_url_env": "SOURCE_DATABASE_URL",
            "sink.connection_url_env": "SINK_DATABASE_URL",
        }
    )
    factory.create("SOURCE_DATABASE_URL")
    factory.create("SINK_DATABASE_URL")

    factory.close()
    factory.close()

    source_engine.dispose.assert_called_once_with()
    sink_engine.dispose.assert_called_once_with()


def test_engine_creation_error_does_not_expose_resolved_url() -> None:
    secret_url = "postgresql://user:very-secret-password@host/db"
    engine_creator = Mock(side_effect=RuntimeError(f"could not parse {secret_url}"))
    factory = SqlEngineFactory(
        getenv=lambda _name: secret_url,
        engine_creator=engine_creator,
    )
    factory.preflight({"source.connection_url_env": "SOURCE_DATABASE_URL"})

    with pytest.raises(SqlEngineFactoryError) as exc_info:
        factory.create("SOURCE_DATABASE_URL")

    assert "SOURCE_DATABASE_URL" in str(exc_info.value)
    assert secret_url not in str(exc_info.value)
    assert "very-secret-password" not in str(exc_info.value)
