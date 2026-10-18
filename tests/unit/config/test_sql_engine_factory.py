"""Unit tests for SQLAlchemy engine construction and ownership."""

from collections.abc import Mapping
from typing import cast
from unittest.mock import Mock, call

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


def test_sql_preflight_rejects_invalid_paths_and_variable_names() -> None:
    getenv = Mock(return_value=None)
    factory = SqlEngineFactory(getenv=getenv, engine_creator=Mock())

    with pytest.raises(SqlEngineFactoryError) as exc_info:
        factory.preflight(
            cast(
                Mapping[str, str],
                {
                    "": "VALID_URL",
                    "processors[0]": "   ",
                    "target": 9,  # Defensive runtime check despite the type hint.
                    "sink": "MISSING_URL",
                    7: "IGNORED_URL",  # Defensive runtime check despite the type hint.
                },
            )
        )

    message = str(exc_info.value)
    assert "invalid configuration path" in message
    assert "non-empty environment-variable name" in message
    assert "MISSING_URL" in message
    assert "VALID_URL" not in message
    assert "IGNORED_URL" not in message
    getenv.assert_called_once_with("MISSING_URL")


@pytest.mark.parametrize("value", [None, 17, "", "   "])
def test_sql_preflight_treats_non_string_or_blank_values_as_missing(value: object) -> None:
    getenv = Mock(return_value=value)
    factory = SqlEngineFactory(getenv=getenv, engine_creator=Mock())

    with pytest.raises(SqlEngineFactoryError, match="DB_URL"):
        factory.preflight({"source": "DB_URL"})

    getenv.assert_called_once_with("DB_URL")


def test_sql_preflight_suppresses_environment_lookup_exception_details() -> None:
    getenv = Mock(side_effect=RuntimeError("postgresql://secret-user:secret-password@db"))
    factory = SqlEngineFactory(getenv=getenv, engine_creator=Mock())

    with pytest.raises(SqlEngineFactoryError) as exc_info:
        factory.preflight({"source": "SOURCE_URL"})

    message = str(exc_info.value)
    assert "SOURCE_URL" in message
    assert "secret-user" not in message
    assert "secret-password" not in message
    assert "postgresql://" not in message


def test_sql_preflight_reads_duplicate_variable_only_once_and_aggregates_errors() -> None:
    getenv = Mock(side_effect=lambda name: "sqlite:///good.db" if name == "GOOD_URL" else None)
    factory = SqlEngineFactory(getenv=getenv, engine_creator=Mock())

    with pytest.raises(SqlEngineFactoryError) as exc_info:
        factory.preflight(
            {
                "source": "GOOD_URL",
                "sink": "MISSING_URL",
                "audit": "MISSING_URL",
            }
        )

    message = str(exc_info.value)
    assert "sink" in message
    assert "audit" in message
    assert "MISSING_URL" in message
    assert getenv.call_args_list == [
        call("GOOD_URL"),
        call("MISSING_URL"),
    ]


def test_failed_second_preflight_invalidates_previous_resolution() -> None:
    factory = SqlEngineFactory(
        getenv=lambda name: "sqlite:///safe.db" if name == "SOURCE_URL" else None,
        engine_creator=Mock(),
    )
    factory.preflight({"source": "SOURCE_URL"})

    with pytest.raises(SqlEngineFactoryError):
        factory.preflight({"sink": "MISSING_URL"})

    with pytest.raises(SqlEngineFactoryError, match="preflight must succeed"):
        factory.create("SOURCE_URL")


def test_preflight_cannot_be_repeated_while_an_engine_is_active() -> None:
    engine = Mock()
    factory = SqlEngineFactory(
        getenv=lambda name: "sqlite:///safe.db",
        engine_creator=Mock(return_value=engine),
    )
    factory.preflight({"source": "SOURCE_URL"})
    factory.create("SOURCE_URL")

    with pytest.raises(SqlEngineFactoryError, match="engines are active"):
        factory.preflight({"source": "SOURCE_URL"})

    factory.close()


def test_create_requires_successful_preflight_and_a_referenced_variable() -> None:
    engine_creator = Mock()
    factory = SqlEngineFactory(
        getenv=lambda name: "sqlite:///safe.db", engine_creator=engine_creator
    )

    with pytest.raises(SqlEngineFactoryError, match="preflight must succeed"):
        factory.create("SOURCE_URL")

    factory.preflight({"source": "SOURCE_URL"})
    with pytest.raises(SqlEngineFactoryError, match="not included"):
        factory.create("OTHER_URL")

    engine_creator.assert_not_called()


def test_create_caches_engine_by_variable_name() -> None:
    engine = Mock()
    engine_creator = Mock(return_value=engine)
    factory = SqlEngineFactory(
        getenv=lambda name: "sqlite:///safe.db", engine_creator=engine_creator
    )
    factory.preflight({"source": "SOURCE_URL", "sink": "SOURCE_URL"})

    assert factory.create("SOURCE_URL") is engine
    assert factory.create("SOURCE_URL") is engine
    engine_creator.assert_called_once_with("sqlite:///safe.db")


def test_engine_creation_error_does_not_disclose_connection_url() -> None:
    secret_url = "postgresql://secret-user:secret-password@db.example/warehouse"
    engine_creator = Mock(side_effect=RuntimeError(f"failed to connect to {secret_url}"))
    factory = SqlEngineFactory(getenv=lambda name: secret_url, engine_creator=engine_creator)
    factory.preflight({"source": "SOURCE_URL"})

    with pytest.raises(SqlEngineFactoryError) as exc_info:
        factory.create("SOURCE_URL")

    message = str(exc_info.value)
    assert "SOURCE_URL" in message
    assert "RuntimeError" in message
    assert secret_url not in message
    assert "secret-password" not in message


def test_close_is_idempotent_and_invalidates_preflight() -> None:
    engine = Mock()
    factory = SqlEngineFactory(
        getenv=lambda name: "sqlite:///safe.db",
        engine_creator=Mock(return_value=engine),
    )
    factory.preflight({"source": "SOURCE_URL"})
    factory.create("SOURCE_URL")

    factory.close()
    factory.close()

    engine.dispose.assert_called_once_with()
    with pytest.raises(SqlEngineFactoryError, match="preflight must succeed"):
        factory.create("SOURCE_URL")


def test_close_attempts_all_disposals_and_suppresses_driver_errors() -> None:
    first_engine = Mock()
    second_engine = Mock()
    first_engine.dispose.side_effect = RuntimeError("secret connection details")
    engine_creator = Mock(side_effect=[first_engine, second_engine])
    factory = SqlEngineFactory(
        getenv=lambda name: "sqlite:///safe.db",
        engine_creator=engine_creator,
    )
    factory.preflight({"first": "FIRST_URL", "second": "SECOND_URL"})
    factory.create("FIRST_URL")
    factory.create("SECOND_URL")

    with pytest.raises(SqlEngineFactoryError) as exc_info:
        factory.close()

    assert "secret connection details" not in str(exc_info.value)
    first_engine.dispose.assert_called_once_with()
    second_engine.dispose.assert_called_once_with()
    with pytest.raises(SqlEngineFactoryError, match="preflight must succeed"):
        factory.create("FIRST_URL")
