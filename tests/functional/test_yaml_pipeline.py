"""Functional tests for the public YAML-to-pipeline path."""

from collections.abc import Callable
from pathlib import Path

import pyarrow.csv as pacsv
import yaml

from etlrelay.config.loader import ConfigLoader
from etlrelay.config.pipeline_builder import PipelineBuilder
from etlrelay.config.sql_engine_factory import SqlEngineFactory
from etlrelay.default_components import create_default_component_catalog
from etlrelay.pipeline import Pipeline
from etlrelay.processors.filter_rows import FilterRows
from etlrelay.processors.rename_columns import RenameColumns
from etlrelay.processors.select_columns import SelectColumns
from etlrelay.readers.csv import CsvReader
from etlrelay.readers.yaml import YamlReader
from etlrelay.security.path import PathValidator
from etlrelay.sinks.file import FileSink
from etlrelay.sources.file import FileSource
from etlrelay.storage.local import LocalFileSystem
from etlrelay.writers.csv import CsvWriter

EnvironmentLookup = Callable[[str], str | None]


def _yaml_runtime(base_path: Path, getenv: EnvironmentLookup | None = None):
    """Construct the same default configuration runtime used by the application."""
    components = create_default_component_catalog(
        sql_engine_factory=SqlEngineFactory(getenv=getenv)
    )
    loader = ConfigLoader(
        LocalFileSystem(path_validator=PathValidator(base_path=base_path)),
        YamlReader(),
        components.config_validator,
    )
    builder = PipelineBuilder(
        source_registry=components.source_registry,
        sink_registry=components.sink_registry,
        processor_registry=components.processor_registry,
        getenv=getenv,
        sql_engine_factory=components.sql_engine_factory,
    )
    return loader, builder


def test_yaml_csv_pipeline_matches_equivalent_direct_python_composition(
    tmp_path: Path,
) -> None:
    """Read, transform, and write data through both composition paths."""
    input_path = tmp_path / "input.csv"
    input_path.write_text(
        "id,amount,label\n1,5,alpha\n2,15,beta\n3,25,gamma\n",
        encoding="utf-8",
    )

    config = {
        "version": 1,
        "source": {
            "type": "file",
            "path": "input.csv",
            "format": "csv",
            "storage": {"type": "local", "base_path": str(tmp_path)},
        },
        # These operations are intentionally order-dependent:
        # select_columns needs "id" before rename_columns changes its name;
        # filter_rows needs "record_id" after the rename.
        "processors": [
            {"type": "select_columns", "columns": ["id", "amount"]},
            {"type": "rename_columns", "mapping": {"id": "record_id"}},
            {
                "type": "filter_rows",
                "column": "record_id",
                "operator": ">",
                "value": 1,
            },
        ],
        "sink": {
            "type": "file",
            "path": "yaml-output.csv",
            "format": "csv",
            "storage": {"type": "local", "base_path": str(tmp_path)},
        },
    }
    (tmp_path / "pipeline.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )

    loader, builder = _yaml_runtime(tmp_path)
    try:
        validated_config = loader.load("pipeline.yaml")
        yaml_pipeline = builder.build(validated_config)
        assert isinstance(yaml_pipeline, Pipeline)
        yaml_pipeline.run()
    finally:
        builder.close()

    # This composition intentionally bypasses ConfigLoader, ConfigValidator,
    # the registries, the config factories, and PipelineBuilder.
    direct_storage = LocalFileSystem(path_validator=PathValidator(base_path=tmp_path))
    direct_pipeline = Pipeline(
        FileSource(
            path="input.csv",
            storage=direct_storage,
            reader=CsvReader(),
        ),
        [
            SelectColumns(["id", "amount"]),
            RenameColumns({"id": "record_id"}),
            FilterRows("record_id", ">", 1),
        ],
        FileSink(
            path="python-output.csv",
            storage=direct_storage,
            writer=CsvWriter(),
        ),
    )
    direct_pipeline.run()

    yaml_table = pacsv.read_csv(str(tmp_path / "yaml-output.csv"))
    direct_table = pacsv.read_csv(str(tmp_path / "python-output.csv"))

    assert yaml_table.column_names == ["record_id", "amount"]
    assert yaml_table.to_pylist() == [
        {"record_id": 2, "amount": 15},
        {"record_id": 3, "amount": 25},
    ]
    assert yaml_table.equals(direct_table)
