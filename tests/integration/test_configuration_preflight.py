"""Assert invalid configuration is rejected before component construction or I/O."""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from etlrelay.config.errors import ConfigurationError
from etlrelay.config.loader import ConfigLoader
from etlrelay.config.pipeline_builder import PipelineBuilder, PipelineBuildError
from etlrelay.config.sql_engine_factory import SqlEngineFactory
from etlrelay.default_components import create_default_component_catalog
from etlrelay.pipeline import Pipeline
from etlrelay.readers.yaml import YamlReader
from etlrelay.security.path import PathValidator
from etlrelay.storage.local import LocalFileSystem

EnvironmentLookup = Callable[[str], str | None]


def _build_loader(base_path: Path, components):
    return ConfigLoader(
        LocalFileSystem(path_validator=PathValidator(base_path=base_path)),
        YamlReader(),
        components.config_validator,
    )


def _build_builder(components, getenv: EnvironmentLookup) -> PipelineBuilder:
    return PipelineBuilder(
        source_registry=components.source_registry,
        sink_registry=components.sink_registry,
        processor_registry=components.processor_registry,
        getenv=getenv,
        sql_engine_factory=components.sql_engine_factory,
    )


def _all_component_factories(components) -> list[object]:
    factories: list[object] = []
    for registry in (
        components.storage_registry,
        components.source_registry,
        components.sink_registry,
        components.processor_registry,
    ):
        for name in registry.names():
            factory = registry.get(name).factory
            if all(factory is not existing for existing in factories):
                factories.append(factory)
    return factories


def _forbid_factory_builds(components, monkeypatch: pytest.MonkeyPatch) -> list[Mock]:
    spies: list[Mock] = []
    for factory in _all_component_factories(components):
        spy = Mock(side_effect=AssertionError("factory must not build on preflight failure"))
        monkeypatch.setattr(factory, "build", spy)
        spies.append(spy)
    return spies


def test_invalid_yaml_configuration_is_rejected_without_component_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine_creator = Mock(name="engine_creator")
    components = create_default_component_catalog(
        sql_engine_factory=SqlEngineFactory(
            getenv=lambda _name: None,
            engine_creator=engine_creator,
        )
    )
    factory_spies = _forbid_factory_builds(components, monkeypatch)
    run_spy = Mock(name="Pipeline.run")
    monkeypatch.setattr(Pipeline, "run", run_spy)

    config = {
        "version": 1,
        "source": {
            "type": "file",
            "path": "input.csv",
            "format": "csv",
            "storage": {"type": "local", "base_path": str(tmp_path)},
        },
        "processors": [{"type": "not_a_supported_processor"}],
        "sink": {
            "type": "file",
            "path": "output.csv",
            "format": "csv",
            "storage": {"type": "local", "base_path": str(tmp_path)},
        },
    }
    (tmp_path / "pipeline.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )

    loader = _build_loader(tmp_path, components)
    with pytest.raises(ConfigurationError, match="not_a_supported_processor"):
        loader.load("pipeline.yaml")

    for spy in factory_spies:
        spy.assert_not_called()
    engine_creator.assert_not_called()
    run_spy.assert_not_called()
    assert not (tmp_path / "output.csv").exists()


@pytest.mark.parametrize("environment_value", [None, ""])
def test_missing_or_empty_sql_environment_variable_fails_before_construction(
    environment_value: str | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "input.csv").write_text(
        "id,amount\n1,5\n",
        encoding="utf-8",
    )
    environment = {} if environment_value is None else {"MISSING_DATABASE_URL": environment_value}
    engine_creator = Mock(name="engine_creator")
    components = create_default_component_catalog(
        sql_engine_factory=SqlEngineFactory(
            getenv=environment.get,
            engine_creator=engine_creator,
        )
    )
    factory_spies = _forbid_factory_builds(components, monkeypatch)
    run_spy = Mock(name="Pipeline.run")
    monkeypatch.setattr(Pipeline, "run", run_spy)

    config = {
        "version": 1,
        "source": {
            "type": "file",
            "path": "input.csv",
            "format": "csv",
            "storage": {"type": "local", "base_path": str(tmp_path)},
        },
        "processors": [],
        "sink": {
            "type": "sql",
            "connection_url_env": "MISSING_DATABASE_URL",
            "table_name": "processed_records",
        },
    }
    (tmp_path / "pipeline.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )

    loader = _build_loader(tmp_path, components)
    validated_config = loader.load("pipeline.yaml")
    builder = _build_builder(components, environment.get)

    with pytest.raises(PipelineBuildError, match="MISSING_DATABASE_URL"):
        builder.build(validated_config)

    for spy in factory_spies:
        spy.assert_not_called()
    engine_creator.assert_not_called()
    run_spy.assert_not_called()
    assert not (tmp_path / "processed_records").exists()
