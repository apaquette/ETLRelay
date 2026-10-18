"""Unit tests for constructing Pipeline objects from validated v1 config."""

from collections.abc import Callable, Mapping
from typing import Any, cast
from unittest.mock import Mock

import pytest

from etlrelay.config.pipeline_builder import PipelineBuilder, PipelineBuildError
from etlrelay.config.registry import ComponentRegistration, ComponentRegistry
from etlrelay.config.sql_engine_factory import SqlEngineFactoryError
from etlrelay.pipeline import Pipeline


class StubConfigValidator:
    """Validator test double; schema validation is outside builder scope."""

    def validate(self, config: object, path: str) -> list[str]:
        return []


def registration(factory: Any) -> ComponentRegistration[Any]:
    return ComponentRegistration(validator=StubConfigValidator(), factory=factory)


def valid_config() -> dict[str, object]:
    return {
        "version": 1,
        "source": {
            "type": "file",
            "path": "input.csv",
            "format": "csv",
            "storage": {"type": "local"},
        },
        "processors": [
            {"type": "select_columns", "columns": ["id", "amount"]},
            {"type": "filter_rows", "column": "amount", "operator": ">=", "value": 0},
            {"type": "rename_columns", "mapping": {"id": "record_id"}},
        ],
        "sink": {
            "type": "file",
            "path": "output.parquet",
            "format": "parquet",
            "storage": {"type": "local"},
        },
    }


@pytest.fixture
def factories() -> dict[str, Mock]:
    result: dict[str, Mock] = {}
    for name in (
        "source_file",
        "source_sql",
        "sink_file",
        "sink_sql",
        "select_columns",
        "rename_columns",
        "filter_rows",
    ):
        factory = Mock(name=name)
        factory.build.return_value = object()
        result[name] = factory
    return result


def builder_for_factories(
    factories: dict[str, Mock],
    environ: Mapping[str, str] | None = None,
    *,
    getenv: Callable[[str], str | None] | None = None,
    sql_engine_factory: object | None = None,
) -> PipelineBuilder:
    """Create a builder with all supported component registrations."""
    if getenv is None:
        values = {} if environ is None else environ
        getenv = values.get

    source_registry = ComponentRegistry(
        {
            "file": registration(factories["source_file"]),
            "sql": registration(factories["source_sql"]),
        }
    )
    sink_registry = ComponentRegistry(
        {
            "file": registration(factories["sink_file"]),
            "sql": registration(factories["sink_sql"]),
        }
    )
    processor_registry = ComponentRegistry(
        {
            "select_columns": registration(factories["select_columns"]),
            "rename_columns": registration(factories["rename_columns"]),
            "filter_rows": registration(factories["filter_rows"]),
        }
    )
    return PipelineBuilder(
        source_registry=source_registry,
        sink_registry=sink_registry,
        processor_registry=processor_registry,
        getenv=getenv,
        sql_engine_factory=sql_engine_factory,  # type: ignore[arg-type]
    )


@pytest.fixture
def builder(factories: dict[str, Mock]) -> PipelineBuilder:
    return builder_for_factories(factories)


def test_build_returns_pipeline_with_registered_components(
    builder: PipelineBuilder,
    factories: dict[str, Mock],
) -> None:
    config = valid_config()
    source_config = cast(Mapping[str, object], config["source"])
    processors = cast(list[Mapping[str, object]], config["processors"])
    sink_config = cast(Mapping[str, object], config["sink"])

    pipeline = builder.build(config)

    assert isinstance(pipeline, Pipeline)
    factories["source_file"].build.assert_called_once_with(source_config)
    factories["select_columns"].build.assert_called_once_with(processors[0])
    factories["filter_rows"].build.assert_called_once_with(processors[1])
    factories["rename_columns"].build.assert_called_once_with(processors[2])
    factories["sink_file"].build.assert_called_once_with(sink_config)
    assert pipeline.source is factories["source_file"].build.return_value
    assert pipeline.sink is factories["sink_file"].build.return_value
    assert pipeline.processors == [
        factories["select_columns"].build.return_value,
        factories["filter_rows"].build.return_value,
        factories["rename_columns"].build.return_value,
    ]


def test_build_preserves_processor_order(
    builder: PipelineBuilder,
    factories: dict[str, Mock],
) -> None:
    config = valid_config()
    config["processors"] = [
        {"type": "rename_columns", "mapping": {"id": "record_id"}},
        {"type": "select_columns", "columns": ["record_id"]},
    ]

    pipeline = builder.build(config)

    assert pipeline.processors == [
        factories["rename_columns"].build.return_value,
        factories["select_columns"].build.return_value,
    ]
    assert factories["rename_columns"].build.call_count == 1
    assert factories["select_columns"].build.call_count == 1


def test_build_accepts_empty_processor_sequence(
    builder: PipelineBuilder,
    factories: dict[str, Mock],
) -> None:
    config = valid_config()
    config["processors"] = []

    pipeline = builder.build(config)

    assert pipeline.processors == []
    factories["select_columns"].build.assert_not_called()
    factories["rename_columns"].build.assert_not_called()
    factories["filter_rows"].build.assert_not_called()


def test_build_does_not_execute_pipeline(
    builder: PipelineBuilder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = Mock(name="Pipeline.run")
    monkeypatch.setattr(Pipeline, "run", run)

    pipeline = builder.build(valid_config())

    assert isinstance(pipeline, Pipeline)
    run.assert_not_called()


@pytest.mark.parametrize(
    ("section", "component_type"),
    [
        ("source", "unsupported_source"),
        ("sink", "unsupported_sink"),
    ],
)
def test_unknown_source_or_sink_type_fails_before_factory_calls(
    builder: PipelineBuilder,
    factories: dict[str, Mock],
    section: str,
    component_type: str,
) -> None:
    config = valid_config()
    component = dict(cast(Mapping[str, object], config[section]))
    component["type"] = component_type
    config[section] = component

    with pytest.raises(PipelineBuildError, match=component_type):
        builder.build(config)

    for factory in factories.values():
        factory.build.assert_not_called()


@pytest.mark.parametrize("component_type", ["unknown", "eval", "python"])
def test_unknown_processor_type_fails_before_constructing_any_component(
    builder: PipelineBuilder,
    factories: dict[str, Mock],
    component_type: str,
) -> None:
    config = valid_config()
    config["processors"] = [
        {"type": "select_columns", "columns": ["id"]},
        {"type": component_type},
    ]

    with pytest.raises(PipelineBuildError, match=component_type):
        builder.build(config)

    for factory in factories.values():
        factory.build.assert_not_called()


def test_sql_source_environment_variable_is_checked_before_construction(
    factories: dict[str, Mock],
) -> None:
    source_config = {
        "type": "sql",
        "connection_url_env": "SOURCE_DATABASE_URL",
        "query": "SELECT 1",
    }
    config = valid_config()
    config["source"] = source_config
    getenv = Mock(return_value="sqlite:///source.db")
    builder = builder_for_factories(factories, getenv=getenv)

    builder.build(config)

    getenv.assert_called_once_with("SOURCE_DATABASE_URL")
    factories["source_sql"].build.assert_called_once_with(source_config)


def test_missing_sink_environment_variable_fails_before_any_factory_call(
    factories: dict[str, Mock],
) -> None:
    config = valid_config()
    config["source"] = {
        "type": "sql",
        "connection_url_env": "SOURCE_DATABASE_URL",
        "query": "SELECT 1",
    }
    config["sink"] = {
        "type": "sql",
        "connection_url_env": "MISSING_SINK_DATABASE_URL",
        "table_name": "target",
    }
    secret_url = "postgresql://user:secret-password@db.example/warehouse"
    getenv = Mock(side_effect={"SOURCE_DATABASE_URL": secret_url}.get)
    builder = builder_for_factories(factories, getenv=getenv)

    with pytest.raises(PipelineBuildError) as exc_info:
        builder.build(config)

    assert "MISSING_SINK_DATABASE_URL" in str(exc_info.value)
    assert secret_url not in str(exc_info.value)
    assert "secret-password" not in str(exc_info.value)
    for factory in factories.values():
        factory.build.assert_not_called()


def test_empty_environment_variable_is_treated_as_missing(
    factories: dict[str, Mock],
) -> None:
    config = valid_config()
    config["source"] = {
        "type": "sql",
        "connection_url_env": "SOURCE_DATABASE_URL",
        "query": "SELECT 1",
    }
    builder = builder_for_factories(factories, {"SOURCE_DATABASE_URL": ""})

    with pytest.raises(PipelineBuildError, match="SOURCE_DATABASE_URL"):
        builder.build(config)

    for factory in factories.values():
        factory.build.assert_not_called()


@pytest.mark.parametrize("section", ["source", "sink"])
@pytest.mark.parametrize("value", [None, "not-a-mapping", 42])
def test_non_mapping_source_or_sink_fails_before_factory_calls(
    builder: PipelineBuilder,
    factories: dict[str, Mock],
    section: str,
    value: object,
) -> None:
    config = valid_config()
    config[section] = value

    with pytest.raises(PipelineBuildError, match=f"'{section}' must be a mapping"):
        builder.build(config)

    for factory in factories.values():
        factory.build.assert_not_called()


@pytest.mark.parametrize("processors", [None, (), "not-a-list", {}])
def test_non_list_processors_fail_before_factory_calls(
    builder: PipelineBuilder,
    factories: dict[str, Mock],
    processors: object,
) -> None:
    config = valid_config()
    config["processors"] = processors

    with pytest.raises(PipelineBuildError, match="'processors' must be a list"):
        builder.build(config)

    for factory in factories.values():
        factory.build.assert_not_called()


@pytest.mark.parametrize("processor_config", [None, "not-a-mapping", 42])
def test_non_mapping_processor_fails_before_factory_calls(
    builder: PipelineBuilder,
    factories: dict[str, Mock],
    processor_config: object,
) -> None:
    config = valid_config()
    config["processors"] = [{"type": "select_columns", "columns": ["id"]}, processor_config]

    with pytest.raises(PipelineBuildError, match=r"processors\[1\] must be a mapping"):
        builder.build(config)

    for factory in factories.values():
        factory.build.assert_not_called()


@pytest.mark.parametrize("component_type", [None, 7, "", "   "])
def test_missing_or_invalid_component_type_fails_before_factory_calls(
    builder: PipelineBuilder,
    factories: dict[str, Mock],
    component_type: object,
) -> None:
    config = valid_config()
    source_config = dict(cast(Mapping[str, object], config["source"]))
    if component_type is None:
        source_config.pop("type")
    else:
        source_config["type"] = component_type
    config["source"] = source_config

    with pytest.raises(
        PipelineBuildError, match=r"source\.type must be a non-empty component type"
    ):
        builder.build(config)

    for factory in factories.values():
        factory.build.assert_not_called()


@pytest.mark.parametrize("section", ["source", "sink"])
@pytest.mark.parametrize("variable_name", [None, 1, "", "   "])
def test_sql_component_requires_non_empty_environment_variable_name(
    factories: dict[str, Mock],
    section: str,
    variable_name: object,
) -> None:
    config = valid_config()
    sql_config: dict[str, object] = {
        "type": "sql",
        "connection_url_env": variable_name,
        "query": "SELECT 1",
        "table_name": "target",
    }
    config[section] = sql_config
    builder = builder_for_factories(factories, {"DATABASE_URL": "sqlite:///test.db"})

    with pytest.raises(PipelineBuildError, match=rf"{section}\.connection_url_env"):
        builder.build(config)

    for factory in factories.values():
        factory.build.assert_not_called()


def test_repeated_sql_environment_variable_is_read_once(
    factories: dict[str, Mock],
) -> None:
    config = valid_config()
    config["source"] = {
        "type": "sql",
        "connection_url_env": "DATABASE_URL",
        "query": "SELECT 1",
    }
    config["sink"] = {
        "type": "sql",
        "connection_url_env": "DATABASE_URL",
        "table_name": "target",
    }
    getenv = Mock(return_value="sqlite:///shared.db")
    builder = builder_for_factories(factories, getenv=getenv)

    builder.build(config)

    getenv.assert_called_once_with("DATABASE_URL")
    factories["source_sql"].build.assert_called_once_with(config["source"])
    factories["sink_sql"].build.assert_called_once_with(config["sink"])


def test_environment_lookup_exception_is_treated_as_missing(
    factories: dict[str, Mock],
) -> None:
    config = valid_config()
    config["source"] = {
        "type": "sql",
        "connection_url_env": "SOURCE_DATABASE_URL",
        "query": "SELECT 1",
    }
    getenv = Mock(side_effect=RuntimeError("lookup failed"))
    builder = builder_for_factories(factories, getenv=getenv)

    with pytest.raises(PipelineBuildError, match="SOURCE_DATABASE_URL") as exc_info:
        builder.build(config)

    assert "lookup failed" not in str(exc_info.value)
    for factory in factories.values():
        factory.build.assert_not_called()


def test_shared_sql_engine_factory_preflight_is_used(
    factories: dict[str, Mock],
) -> None:
    config = valid_config()
    source_config = {
        "type": "sql",
        "connection_url_env": "SOURCE_DATABASE_URL",
        "query": "SELECT 1",
    }
    config["source"] = source_config
    sql_engine_factory = Mock()
    builder = builder_for_factories(
        factories,
        sql_engine_factory=sql_engine_factory,
    )

    builder.build(config)

    sql_engine_factory.preflight.assert_called_once_with(
        {"source.connection_url_env": "SOURCE_DATABASE_URL"}
    )
    factories["source_sql"].build.assert_called_once_with(source_config)


def test_sql_engine_preflight_error_is_wrapped_before_construction(
    factories: dict[str, Mock],
) -> None:
    config = valid_config()
    config["source"] = {
        "type": "sql",
        "connection_url_env": "SOURCE_DATABASE_URL",
        "query": "SELECT 1",
    }
    sql_engine_factory = Mock()
    sql_engine_factory.preflight.side_effect = SqlEngineFactoryError("environment is missing")
    builder = builder_for_factories(
        factories,
        sql_engine_factory=sql_engine_factory,
    )

    with pytest.raises(PipelineBuildError, match="environment is missing"):
        builder.build(config)

    for factory in factories.values():
        factory.build.assert_not_called()
    sql_engine_factory.close.assert_not_called()


def test_factory_failure_without_sql_references_does_not_close_sql_engine_factory(
    factories: dict[str, Mock],
) -> None:
    factories["source_file"].build.side_effect = RuntimeError("source construction failed")
    sql_engine_factory = Mock()
    builder = builder_for_factories(
        factories,
        sql_engine_factory=sql_engine_factory,
    )

    with pytest.raises(RuntimeError, match="source construction failed"):
        builder.build(valid_config())

    sql_engine_factory.close.assert_not_called()


def test_factory_failure_with_sql_references_closes_sql_engine_factory(
    factories: dict[str, Mock],
) -> None:
    config = valid_config()
    config["source"] = {
        "type": "sql",
        "connection_url_env": "SOURCE_DATABASE_URL",
        "query": "SELECT 1",
    }
    factories["source_sql"].build.side_effect = RuntimeError("source construction failed")
    sql_engine_factory = Mock()
    builder = builder_for_factories(
        factories,
        sql_engine_factory=sql_engine_factory,
    )

    with pytest.raises(RuntimeError, match="source construction failed"):
        builder.build(config)

    sql_engine_factory.close.assert_called_once_with()


def test_cleanup_failure_does_not_replace_original_factory_failure(
    factories: dict[str, Mock],
) -> None:
    config = valid_config()
    config["source"] = {
        "type": "sql",
        "connection_url_env": "SOURCE_DATABASE_URL",
        "query": "SELECT 1",
    }
    factories["source_sql"].build.side_effect = RuntimeError("original construction failure")
    sql_engine_factory = Mock()
    sql_engine_factory.close.side_effect = RuntimeError("cleanup failure")
    builder = builder_for_factories(
        factories,
        sql_engine_factory=sql_engine_factory,
    )

    with pytest.raises(RuntimeError, match="original construction failure") as exc_info:
        builder.build(config)

    assert "cleanup failure" not in str(exc_info.value)
    sql_engine_factory.close.assert_called_once_with()


def test_close_is_noop_without_sql_engine_factory(
    builder: PipelineBuilder,
) -> None:
    builder.close()


def test_close_releases_shared_sql_engine_factory(
    factories: dict[str, Mock],
) -> None:
    sql_engine_factory = Mock()
    builder = builder_for_factories(
        factories,
        sql_engine_factory=sql_engine_factory,
    )

    builder.close()

    sql_engine_factory.close.assert_called_once_with()


def test_close_wraps_sql_engine_factory_error(
    factories: dict[str, Mock],
) -> None:
    sql_engine_factory = Mock()
    sql_engine_factory.close.side_effect = SqlEngineFactoryError("engine cleanup failed")
    builder = builder_for_factories(
        factories,
        sql_engine_factory=sql_engine_factory,
    )

    with pytest.raises(PipelineBuildError, match="engine cleanup failed"):
        builder.close()
