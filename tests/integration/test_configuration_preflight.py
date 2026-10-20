"""Assert invalid configuration is rejected before component construction or I/O."""

from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO
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


@pytest.mark.parametrize(
    ("invalid_case", "expected_error"),
    [
        ("unknown_root_field", "unexpected"),
        ("missing_sink_path", "sink.path"),
        ("unsupported_storage", "source.storage.type"),
        ("unsupported_format", "sink.format"),
        ("unregistered_processor", "os.system"),
        ("invalid_sql_parameters", "source.parameters"),
    ],
)
def test_invalid_configurations_fail_without_data_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_case: str,
    expected_error: str,
) -> None:
    source_config: dict[str, object] = {
        "type": "file",
        "path": "input.csv",
        "format": "csv",
        "storage": {"type": "local", "base_path": str(tmp_path)},
    }
    sink_config: dict[str, object] = {
        "type": "file",
        "path": "output.csv",
        "format": "csv",
        "storage": {"type": "local", "base_path": str(tmp_path)},
    }
    config: dict[str, object] = {
        "version": 1,
        "source": source_config,
        "processors": [],
        "sink": sink_config,
    }

    if invalid_case == "unknown_root_field":
        config["unexpected"] = True
    elif invalid_case == "missing_sink_path":
        sink_config.pop("path")
    elif invalid_case == "unsupported_storage":
        source_config["storage"] = {"type": "unknown_storage"}
    elif invalid_case == "unsupported_format":
        sink_config["format"] = "unknown_format"
    elif invalid_case == "unregistered_processor":
        config["processors"] = [{"type": "os.system"}]
    elif invalid_case == "invalid_sql_parameters":
        source_config.clear()
        source_config.update(
            {
                "type": "sql",
                "connection_url_env": "DATABASE_URL",
                "query": "SELECT :identifier",
                "parameters": {"identifier": [1, 2]},
            }
        )
    else:
        pytest.fail(f"Unknown test case: {invalid_case}")

    output_path = tmp_path / "output.csv"
    output_path.write_bytes(b"original output")

    (tmp_path / "pipeline.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )

    getenv = Mock(return_value="sqlite:///test.db")
    engine_creator = Mock()

    components = create_default_component_catalog(
        sql_engine_factory=SqlEngineFactory(
            getenv=getenv,
            engine_creator=engine_creator,
        )
    )

    factory_spies = _forbid_factory_builds(components, monkeypatch)

    run_spy = Mock(name="Pipeline.run")
    monkeypatch.setattr(Pipeline, "run", run_spy)

    # Configuration loading is permitted to read pipeline.yaml,
    # but must not open pipeline data files.
    original_open_read = LocalFileSystem.open_read
    read_paths: list[str] = []

    def tracked_open_read(
        filesystem: LocalFileSystem,
        path: str,
    ) -> BinaryIO:
        read_paths.append(path)
        return original_open_read(filesystem, path)

    monkeypatch.setattr(
        LocalFileSystem,
        "open_read",
        tracked_open_read,
    )

    write_spy = Mock(
        side_effect=AssertionError("Data output must not be opened during configuration validation")
    )
    monkeypatch.setattr(LocalFileSystem, "open_write", write_spy)

    loader = _build_loader(tmp_path, components)

    with pytest.raises(ConfigurationError) as exc_info:
        loader.load("pipeline.yaml")

    assert expected_error in str(exc_info.value)

    assert read_paths == ["pipeline.yaml"]
    write_spy.assert_not_called()

    for spy in factory_spies:
        spy.assert_not_called()

    getenv.assert_not_called()
    engine_creator.assert_not_called()
    run_spy.assert_not_called()

    assert output_path.read_bytes() == b"original output"


def test_multiple_sql_references_fail_before_engine_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_url = "sqlite:///source.db"

    environment = {
        "SOURCE_DATABASE_URL": secret_url,
    }

    getenv = Mock(side_effect=environment.get)
    engine_creator = Mock()

    components = create_default_component_catalog(
        sql_engine_factory=SqlEngineFactory(
            getenv=getenv,
            engine_creator=engine_creator,
        )
    )

    factory_spies = _forbid_factory_builds(components, monkeypatch)

    run_spy = Mock(name="Pipeline.run")
    monkeypatch.setattr(Pipeline, "run", run_spy)

    config = {
        "version": 1,
        "source": {
            "type": "sql",
            "connection_url_env": "SOURCE_DATABASE_URL",
            "query": "SELECT id FROM records",
        },
        "processors": [],
        "sink": {
            "type": "sql",
            "connection_url_env": "MISSING_SINK_DATABASE_URL",
            "table_name": "processed_records",
        },
    }

    (tmp_path / "pipeline.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )

    loader = _build_loader(tmp_path, components)
    validated_config = loader.load("pipeline.yaml")

    builder = _build_builder(components, getenv)

    with pytest.raises(PipelineBuildError) as exc_info:
        builder.build(validated_config)

    message = str(exc_info.value)

    assert "MISSING_SINK_DATABASE_URL" in message
    assert secret_url not in message

    getenv.assert_any_call("SOURCE_DATABASE_URL")
    getenv.assert_any_call("MISSING_SINK_DATABASE_URL")

    for spy in factory_spies:
        spy.assert_not_called()

    engine_creator.assert_not_called()
    run_spy.assert_not_called()


def test_successful_build_defers_pipeline_file_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = {
        "version": 1,
        "source": {
            "type": "file",
            "path": "input.csv",
            "format": "csv",
            "storage": {
                "type": "local",
                "base_path": str(tmp_path),
            },
        },
        "processors": [],
        "sink": {
            "type": "file",
            "path": "output.csv",
            "format": "csv",
            "storage": {
                "type": "local",
                "base_path": str(tmp_path),
            },
        },
    }

    (tmp_path / "pipeline.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )

    components = create_default_component_catalog()
    loader = _build_loader(tmp_path, components)
    validated_config = loader.load("pipeline.yaml")

    # After loading the configuration, neither construction nor
    # registration resolution should open pipeline data files.
    read_spy = Mock(
        side_effect=AssertionError("Pipeline input must not be opened during construction")
    )
    write_spy = Mock(
        side_effect=AssertionError("Pipeline output must not be opened during construction")
    )

    monkeypatch.setattr(LocalFileSystem, "open_read", read_spy)
    monkeypatch.setattr(LocalFileSystem, "open_write", write_spy)

    run_spy = Mock(name="Pipeline.run")
    monkeypatch.setattr(Pipeline, "run", run_spy)

    builder = _build_builder(components, lambda _name: None)

    pipeline = builder.build(validated_config)

    assert isinstance(pipeline, Pipeline)

    read_spy.assert_not_called()
    write_spy.assert_not_called()
    run_spy.assert_not_called()

    assert not (tmp_path / "output.csv").exists()
