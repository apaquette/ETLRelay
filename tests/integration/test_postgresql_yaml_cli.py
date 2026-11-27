"""PostgreSQL YAML and CLI integration coverage."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from sqlalchemy import create_engine, text
from typer.testing import CliRunner

import etlrelay.cli as cli

runner = CliRunner()


def test_postgresql_yaml_pipeline_executes_through_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Validate and execute a batched PostgreSQL source-to-sink YAML pipeline."""
    url = os.environ.get("ETLRELAY_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("ETLRELAY_TEST_POSTGRES_URL is not set")

    source_table = f"etlrelay_yaml_source_{uuid4().hex}"
    sink_table = f"etlrelay_yaml_sink_{uuid4().hex}"
    engine = create_engine(url)

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f'CREATE TABLE "{source_table}" '
                    "(id BIGINT PRIMARY KEY, name TEXT NOT NULL)"
                )
            )
            connection.execute(
                text(
                    f'CREATE TABLE "{sink_table}" '
                    "(id BIGINT PRIMARY KEY, name TEXT NOT NULL)"
                )
            )
            connection.execute(
                text(
                    f'INSERT INTO "{source_table}" (id, name) VALUES '
                    "(1, 'Ada'), (2, 'Grace'), (3, 'Linus')"
                )
            )

        monkeypatch.setenv("ETLRELAY_YAML_POSTGRES_URL", url)
        config = {
            "version": 1,
            "source": {
                "type": "sql",
                "connection_url_env": "ETLRELAY_YAML_POSTGRES_URL",
                "query": f'SELECT id, name FROM "{source_table}" ORDER BY id',
                "batch_size": 2,
                "schema": {
                    "fields": [
                        {"name": "id", "type": "int64", "nullable": False},
                        {"name": "name", "type": "string", "nullable": False},
                    ]
                },
            },
            "processors": [],
            "sink": {
                "type": "sql",
                "connection_url_env": "ETLRELAY_YAML_POSTGRES_URL",
                "table_name": sink_table,
            },
        }
        config_path = tmp_path / "pipeline.yml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

        validation = runner.invoke(cli.app, ["validate", str(config_path)])
        assert validation.exit_code == 0, validation.output

        execution = runner.invoke(cli.app, ["run", str(config_path)])
        assert execution.exit_code == 0, (
            f"Output: {execution.output}\nException: {execution.exception}"
        )

        with engine.connect() as connection:
            rows = connection.execute(
                text(f'SELECT id, name FROM "{sink_table}" ORDER BY id')
            ).mappings().all()
        assert [dict(row) for row in rows] == [
            {"id": 1, "name": "Ada"},
            {"id": 2, "name": "Grace"},
            {"id": 3, "name": "Linus"},
        ]
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP TABLE IF EXISTS "{sink_table}"'))
            connection.execute(text(f'DROP TABLE IF EXISTS "{source_table}"'))
        engine.dispose()
