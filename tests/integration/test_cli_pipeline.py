"""Integration tests for complete CLI pipeline workflows."""

from pathlib import Path
from typing import Any

import yaml
from typer.testing import CliRunner

import etlrelay.cli as cli

runner = CliRunner()


def _write_pipeline_config(
    directory: Path,
    *,
    source_path: str = "input.csv",
    sink_path: str = "output.csv",
    processors: list[dict[str, Any]] | None = None,
) -> Path:
    """Write a pipeline configuration using local CSV storage."""
    storage = {
        "type": "local",
        "base_path": str(directory.resolve()),
    }
    configuration = {
        "version": 1,
        "source": {
            "type": "file",
            "path": source_path,
            "format": "csv",
            "storage": storage,
        },
        "processors": [] if processors is None else processors,
        "sink": {
            "type": "file",
            "path": sink_path,
            "format": "csv",
            "storage": storage,
        },
    }

    config_path = directory / "pipeline.yml"
    config_path.write_text(
        yaml.safe_dump(configuration, sort_keys=False),
        encoding="utf-8",
    )
    return config_path


def test_run_executes_complete_csv_pipeline(
    tmp_path: Path,
) -> None:
    """Integrate configuration loading, source, processors, and sink."""
    (tmp_path / "input.csv").write_text(
        "id,amount,state\n1,10,ready\n2,-2,skip\n3,0,ready\n",
        encoding="utf-8",
    )
    config_path = _write_pipeline_config(
        tmp_path,
        processors=[
            {"type": "select_columns", "columns": ["id", "amount"]},
            {
                "type": "filter_rows",
                "column": "amount",
                "operator": ">",
                "value": 0,
            },
            {"type": "rename_columns", "mapping": {"id": "record_id"}},
        ],
    )

    result = runner.invoke(
        cli.app,
        ["run", str(config_path)],
    )

    assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
    assert f"Pipeline completed: {config_path}" in result.output
    assert (tmp_path / "output.csv").read_text(encoding="utf-8") == ('"record_id","amount"\n1,10\n')


def test_validate_does_not_execute_pipeline_or_create_output(
    tmp_path: Path,
) -> None:
    """Validate configuration without running its data transformations."""
    (tmp_path / "input.csv").write_text(
        "id,amount\n1,10\n",
        encoding="utf-8",
    )
    config_path = _write_pipeline_config(
        tmp_path,
        processors=[
            {"type": "select_columns", "columns": ["missing_column"]},
        ],
    )
    output_path = tmp_path / "output.csv"

    result = runner.invoke(
        cli.app,
        ["validate", str(config_path)],
    )

    assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
    assert f"Pipeline configuration is valid: {config_path}" in result.output
    assert not output_path.exists()


def test_validate_rejects_invalid_configuration(
    tmp_path: Path,
) -> None:
    """Report an invalid pipeline schema using the validation exit code."""
    config_path = tmp_path / "invalid.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "version": 999,
                "source": {},
                "processors": [],
                "sink": {},
            },
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        cli.app,
        ["validate", str(config_path)],
    )

    assert result.exit_code == 3
    assert "Invalid pipeline configuration" in result.output
    assert not (tmp_path / "output.csv").exists()


def test_run_reports_missing_source_as_execution_failure(
    tmp_path: Path,
) -> None:
    """Distinguish runtime source failures from configuration failures."""
    config_path = _write_pipeline_config(
        tmp_path,
        source_path="missing-input.csv",
    )

    result = runner.invoke(
        cli.app,
        ["run", str(config_path)],
    )

    assert result.exit_code == 4
    assert "Pipeline execution failed" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "output.csv").exists()


def test_run_processor_failure_does_not_leak_sensitive_payload(
    tmp_path: Path,
) -> None:
    """Verify safe error presentation when a real processor fails."""
    payload_sentinel = "INTEGRATION_SENSITIVE_PAYLOAD_4A91"
    (tmp_path / "input.csv").write_text(
        f"id,payload\n1,{payload_sentinel}\n",
        encoding="utf-8",
    )
    config_path = _write_pipeline_config(
        tmp_path,
        processors=[
            {"type": "select_columns", "columns": ["missing_column"]},
        ],
    )

    result = runner.invoke(
        cli.app,
        ["run", str(config_path)],
    )

    assert result.exit_code == 4
    assert "Pipeline execution failed" in result.output
    assert "Traceback" not in result.output
    assert payload_sentinel not in result.output
    assert not (tmp_path / "output.csv").exists()


def test_run_sink_failure_returns_execution_error(
    tmp_path: Path,
) -> None:
    """Report a real sink write failure without exposing a traceback."""
    (tmp_path / "input.csv").write_text(
        "id,amount\n1,10\n",
        encoding="utf-8",
    )
    # A directory at the output path makes opening it as a CSV file fail.
    (tmp_path / "output.csv").mkdir()
    config_path = _write_pipeline_config(tmp_path)

    result = runner.invoke(
        cli.app,
        ["run", str(config_path)],
    )

    assert result.exit_code == 4
    assert "Pipeline execution failed" in result.output
    assert "Traceback" not in result.output
    assert (tmp_path / "output.csv").is_dir()
