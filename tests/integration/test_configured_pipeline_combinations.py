"""Exercise every source/sink combination in the v1 configuration contract."""

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import pytest
import yaml
from sqlalchemy import create_engine

from etlrelay.config.loader import ConfigLoader
from etlrelay.config.pipeline_builder import PipelineBuilder
from etlrelay.config.sql_engine_factory import SqlEngineFactory
from etlrelay.default_components import create_default_component_catalog
from etlrelay.readers.yaml import YamlReader
from etlrelay.security.path import PathValidator
from etlrelay.storage.local import LocalFileSystem

EnvironmentLookup = Callable[[str], str | None]


CASES = [
    ("csv", "csv"),
    ("csv", "parquet"),
    ("parquet", "csv"),
    ("parquet", "parquet"),
    ("csv", "sql"),
    ("parquet", "sql"),
    ("sql", "csv"),
    ("sql", "parquet"),
    ("sql", "sql"),
]


def _sqlite_url(path: Path) -> str:
    """Return a SQLAlchemy URL for an absolute local SQLite database path."""
    return f"sqlite:///{path.resolve()}"


def _seed_resources(base_path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = [
        {"id": 1, "amount": 5, "label": "alpha"},
        {"id": 2, "amount": 15, "label": "beta"},
        {"id": 3, "amount": 25, "label": "gamma"},
    ]
    (base_path / "input.csv").write_text(
        "id,amount,label\n1,5,alpha\n2,15,beta\n3,25,gamma\n",
        encoding="utf-8",
    )
    pq.write_table(
        pa.Table.from_pylist(records),
        str(base_path / "input.parquet"),
    )

    with sqlite3.connect(base_path / "source.db") as connection:
        connection.execute("CREATE TABLE source_records (id INTEGER, amount INTEGER, label TEXT)")
        connection.executemany(
            "INSERT INTO source_records (id, amount, label) VALUES (?, ?, ?)",
            [(record["id"], record["amount"], record["label"]) for record in records],
        )

    with sqlite3.connect(base_path / "sink.db") as connection:
        connection.execute(
            "CREATE TABLE processed_records (id INTEGER, amount INTEGER, label TEXT)"
        )
    return records


def _read_file(path: Path, file_format: str) -> list[dict[str, object]]:
    if file_format == "csv":
        table = pacsv.read_csv(str(path))
    else:
        table = pq.read_table(str(path))
    return table.to_pylist()


def _build_runtime(base_path: Path, getenv: EnvironmentLookup):
    components = create_default_component_catalog(
        sql_engine_factory=SqlEngineFactory(
            getenv=getenv,
            engine_creator=create_engine,
        )
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


@pytest.mark.parametrize(("source_kind", "sink_kind"), CASES)
def test_supported_source_sink_combination_runs_end_to_end(
    source_kind: str,
    sink_kind: str,
    tmp_path: Path,
) -> None:
    expected_records = _seed_resources(tmp_path)
    environment = {
        "ETLRELAY_SOURCE_DATABASE_URL": _sqlite_url(tmp_path / "source.db"),
        "ETLRELAY_SINK_DATABASE_URL": _sqlite_url(tmp_path / "sink.db"),
    }

    if source_kind == "sql":
        source_config: dict[str, object] = {
            "type": "sql",
            "connection_url_env": "ETLRELAY_SOURCE_DATABASE_URL",
            "query": "SELECT id, amount, label FROM source_records ORDER BY id",
        }
    else:
        source_config = {
            "type": "file",
            "path": f"input.{source_kind}",
            "format": source_kind,
            "storage": {"type": "local", "base_path": str(tmp_path)},
        }

    if sink_kind == "sql":
        sink_config: dict[str, object] = {
            "type": "sql",
            "connection_url_env": "ETLRELAY_SINK_DATABASE_URL",
            "table_name": "processed_records",
        }
    else:
        sink_config = {
            "type": "file",
            "path": f"output.{sink_kind}",
            "format": sink_kind,
            "storage": {"type": "local", "base_path": str(tmp_path)},
        }

    config = {
        "version": 1,
        "source": source_config,
        "processors": [],
        "sink": sink_config,
    }
    (tmp_path / "pipeline.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )

    loader, builder = _build_runtime(tmp_path, environment.get)
    try:
        pipeline = builder.build(loader.load("pipeline.yaml"))
        pipeline.run()
    finally:
        builder.close()

    if sink_kind == "sql":
        with sqlite3.connect(tmp_path / "sink.db") as connection:
            rows = connection.execute(
                "SELECT id, amount, label FROM processed_records ORDER BY id"
            ).fetchall()
        actual_records = [{"id": row[0], "amount": row[1], "label": row[2]} for row in rows]
    else:
        actual_records = _read_file(tmp_path / f"output.{sink_kind}", sink_kind)

    assert actual_records == expected_records
