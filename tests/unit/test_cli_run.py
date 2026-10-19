"""Unit tests for CLI pipeline execution."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from typer.testing import CliRunner

import etlrelay.cli as cli
from etlrelay.security.path import PathValidationError
from etlrelay.storage.filesystem import FileSystemError

runner = CliRunner()


def _write_file_pipeline_config(
    config_path: Path,
    *,
    base_path: Path,
    source_path: str = "input.csv",
    sink_path: str = "output.csv",
    processors: list[dict[str, object]] | None = None,
) -> None:
    """Write a valid file-to-file pipeline configuration."""
    config = {
        "version": 1,
        "source": {
            "type": "file",
            "path": source_path,
            "format": "csv",
            "storage": {
                "type": "local",
                "base_path": str(base_path),
            },
        },
        "processors": [] if processors is None else processors,
        "sink": {
            "type": "file",
            "path": sink_path,
            "format": "csv",
            "storage": {
                "type": "local",
                "base_path": str(base_path),
            },
        },
    }
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )


def _patch_run_loader_failure(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    """Make the run command's configuration loader raise an exception."""

    class FailingConfigLoader:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def load(self, _filename: str) -> None:
            raise error

    monkeypatch.setattr(cli, "ConfigLoader", FailingConfigLoader)


def _patch_run_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    builder: object,
) -> None:
    """Stub configuration loading and inject a controlled pipeline builder."""

    class SuccessfulConfigLoader:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def load(self, _filename: str) -> object:
            return object()

    monkeypatch.setattr(cli, "ConfigLoader", SuccessfulConfigLoader)
    monkeypatch.setattr(cli, "PipelineBuilder", lambda **_kwargs: builder)


def test_run_executes_pipeline_and_writes_processed_output(
    tmp_path: Path,
) -> None:
    """Execute a complete local file pipeline through the CLI."""
    source = tmp_path / "input.csv"
    source.write_text(
        "id,amount,state\n1,10,ready\n2,-2,skip\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "pipeline.yml"
    _write_file_pipeline_config(
        config_path,
        base_path=tmp_path,
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

    result = runner.invoke(cli.app, ["run", str(config_path)])

    assert result.exit_code == 0, (result.output, result.exception)
    assert f"Pipeline completed: {config_path}" in result.output
    assert (tmp_path / "output.csv").read_text(encoding="utf-8") == ('"record_id","amount"\n1,10\n')


def test_run_invalid_configuration_exits_with_code_3(
    tmp_path: Path,
) -> None:
    """Report schema failures as configuration errors."""
    config_path = tmp_path / "pipeline.yml"
    config_path.write_text(
        "version: 1\nsource: {}\nprocessors: []\nsink: {}\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["run", str(config_path)])

    assert result.exit_code == 3
    assert "Invalid pipeline configuration" in result.output


def test_run_missing_sql_environment_variable_exits_with_code_3(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Treat SQL environment preflight failures as configuration errors."""
    variable = "ETLRELAY_TEST_SOURCE_DATABASE_URL"
    monkeypatch.delenv(variable, raising=False)

    config_path = tmp_path / "pipeline.yml"
    config = {
        "version": 1,
        "source": {
            "type": "sql",
            "connection_url_env": variable,
            "query": "SELECT 1",
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
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["run", str(config_path)])

    assert result.exit_code == 3
    assert variable in result.output
    assert "Pipeline execution failed" not in result.output


def test_run_source_failure_exits_with_code_4(
    tmp_path: Path,
) -> None:
    """Report an input failure as a pipeline execution error."""
    config_path = tmp_path / "pipeline.yml"
    _write_file_pipeline_config(
        config_path,
        base_path=tmp_path,
        source_path="missing-input.csv",
    )

    result = runner.invoke(cli.app, ["run", str(config_path)])

    assert result.exit_code == 4
    assert "Pipeline execution failed" in result.output
    assert "Traceback" not in result.output
    assert "No such file or directory" not in result.output


def test_run_processor_failure_exits_with_code_4(
    tmp_path: Path,
) -> None:
    """Report a processing error when a configured column is missing."""
    (tmp_path / "input.csv").write_text(
        "id,amount\n1,10\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "pipeline.yml"
    _write_file_pipeline_config(
        config_path,
        base_path=tmp_path,
        processors=[
            {"type": "select_columns", "columns": ["missing_column"]},
        ],
    )

    result = runner.invoke(cli.app, ["run", str(config_path)])

    assert result.exit_code == 4
    assert "Pipeline execution failed" in result.output
    assert "Traceback" not in result.output
    assert "missing_column" not in result.output


def test_run_sink_failure_exits_with_code_4(
    tmp_path: Path,
) -> None:
    """Report an output failure without exposing raw exception details."""
    (tmp_path / "input.csv").write_text(
        "id,amount\n1,10\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "pipeline.yml"
    _write_file_pipeline_config(
        config_path,
        base_path=tmp_path,
        sink_path="missing-directory/output.csv",
    )

    result = runner.invoke(cli.app, ["run", str(config_path)])

    assert result.exit_code == 4
    assert "Pipeline execution failed" in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    ("problem_mark", "expected_message"),
    [
        (None, "Invalid YAML syntax."),
        (
            SimpleNamespace(line=2, column=4),
            "Invalid YAML syntax at line 3, column 5.",
        ),
    ],
)
def test_run_yaml_error_reports_safe_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    problem_mark: object | None,
    expected_message: str,
) -> None:
    """Handle YAML failures with or without source-location information."""
    pipeline = tmp_path / "pipeline.yml"
    error = yaml.YAMLError("sensitive parser detail")

    if problem_mark is not None:
        error.problem_mark = problem_mark  # type: ignore[attr-defined]

    _patch_run_loader_failure(monkeypatch, error)

    result = CliRunner().invoke(cli.app, ["run", str(pipeline)])

    assert result.exit_code == 3
    assert expected_message in result.output
    assert "sensitive parser detail" not in result.output


@pytest.mark.parametrize(
    ("error_type", "file_exists", "expected_message"),
    [
        (
            PermissionError,
            True,
            "Permission denied reading pipeline configuration",
        ),
        (
            OSError,
            False,
            "Pipeline configuration file does not exist",
        ),
        (
            OSError,
            True,
            "Unable to read pipeline configuration file",
        ),
        (
            PathValidationError,
            True,
            "Unable to read pipeline configuration file",
        ),
    ],
)
def test_run_filesystem_errors_are_reported_safely(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error_type: type[Exception],
    file_exists: bool,
    expected_message: str,
) -> None:
    """Map filesystem failures to safe, actionable validation errors."""
    pipeline = tmp_path / "pipeline.yml"
    if file_exists:
        pipeline.write_text("placeholder", encoding="utf-8")

    _patch_run_loader_failure(
        monkeypatch,
        error_type("sensitive filesystem detail"),
    )

    result = CliRunner().invoke(cli.app, ["run", str(pipeline)])

    assert result.exit_code == 3
    assert expected_message in result.output
    assert "sensitive filesystem detail" not in result.output


def test_run_filesystem_error_for_existing_config_reports_read_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Distinguish an existing unreadable configuration from a missing file."""
    pipeline = tmp_path / "pipeline.yml"
    pipeline.write_text("placeholder", encoding="utf-8")

    _patch_run_loader_failure(
        monkeypatch,
        FileSystemError("sensitive filesystem detail"),
    )

    result = CliRunner().invoke(cli.app, ["run", str(pipeline)])

    assert result.exit_code == 3
    assert "Unable to read pipeline configuration file" in result.output
    assert "sensitive filesystem detail" not in result.output


def test_run_unexpected_loader_failure_returns_code_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Hide unexpected configuration-loading exception details."""
    pipeline = tmp_path / "pipeline.yml"
    _patch_run_loader_failure(
        monkeypatch,
        RuntimeError("sensitive internal detail"),
    )

    result = CliRunner().invoke(cli.app, ["run", str(pipeline)])

    assert result.exit_code == 1
    assert "Unexpected error while loading pipeline configuration." in result.output
    assert "sensitive internal detail" not in result.output


def test_run_unexpected_build_failure_returns_code_1_and_closes_builder(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Handle unexpected builder failures and still release resources."""
    pipeline = tmp_path / "pipeline.yml"

    class FailingBuilder:
        closed = False

        def build(self, _config: object) -> None:
            raise RuntimeError("sensitive build detail")

        def close(self) -> None:
            self.closed = True

    builder = FailingBuilder()
    _patch_run_dependencies(monkeypatch, builder)

    result = CliRunner().invoke(cli.app, ["run", str(pipeline)])

    assert result.exit_code == 1
    assert "Unexpected error while constructing the pipeline." in result.output
    assert "sensitive build detail" not in result.output
    assert builder.closed


def test_run_cleanup_failure_returns_code_4(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report cleanup failures even after successful pipeline execution."""
    pipeline = tmp_path / "pipeline.yml"

    class SuccessfulPipeline:
        ran = False

        def run(self) -> None:
            self.ran = True

    class FailingCleanupBuilder:
        closed = False

        def __init__(self) -> None:
            self.execution_pipeline = SuccessfulPipeline()

        def build(self, _config: object) -> SuccessfulPipeline:
            return self.execution_pipeline

        def close(self) -> None:
            self.closed = True
            raise RuntimeError("sensitive cleanup detail")

    builder = FailingCleanupBuilder()
    _patch_run_dependencies(monkeypatch, builder)

    result = CliRunner().invoke(cli.app, ["run", str(pipeline)])

    assert result.exit_code == 4
    assert builder.execution_pipeline.ran
    assert builder.closed
    assert "runtime resource cleanup failed" in result.output
    assert "sensitive cleanup detail" not in result.output


def test_run_filesystem_error_for_missing_config_reports_missing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report a missing configuration file when loading raises FileSystemError."""
    pipeline = tmp_path / "missing.yml"

    _patch_run_loader_failure(
        monkeypatch,
        FileSystemError("sensitive filesystem detail"),
    )

    result = CliRunner().invoke(cli.app, ["run", str(pipeline)])

    assert result.exit_code == 3
    assert f"Pipeline configuration file does not exist: {pipeline}" in result.output
    assert "sensitive filesystem detail" not in result.output
