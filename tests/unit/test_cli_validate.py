"""CLI tests for YAML pipeline validation."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

import etlrelay.cli as cli
from etlrelay.cli import app
from etlrelay.config.errors import ConfigurationError
from etlrelay.security.path import PathValidationError
from etlrelay.storage.filesystem import FileSystemError
from etlrelay.storage.local import LocalFileSystem

runner = CliRunner()


def _valid_config(base_path: Path) -> dict[str, object]:
    """Return a valid file-to-file pipeline configuration."""
    return {
        "version": 1,
        "source": {
            "type": "file",
            "path": "input.csv",
            "format": "csv",
            "storage": {"type": "local", "base_path": str(base_path)},
        },
        "processors": [],
        "sink": {
            "type": "file",
            "path": "output.csv",
            "format": "csv",
            "storage": {"type": "local", "base_path": str(base_path)},
        },
    }


def _write_config(path: Path, config: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def _patch_config_loader_failure(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    """Replace ConfigLoader with one that raises the supplied exception."""

    class FailingConfigLoader:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def load(self, _filename: str) -> None:
            raise error

    monkeypatch.setattr(cli, "ConfigLoader", FailingConfigLoader)


def test_validate_accepts_valid_pipeline_configuration(tmp_path: Path) -> None:
    """A supported YAML configuration exits successfully when valid."""
    pipeline_path = tmp_path / "pipeline.yaml"
    _write_config(pipeline_path, _valid_config(tmp_path))

    result = runner.invoke(app, ["validate", str(pipeline_path)])

    assert result.exit_code == 0
    assert "valid" in result.output.lower()
    assert pipeline_path.name in result.output
    assert "traceback" not in result.output.lower()


def test_validate_reports_missing_configuration_file(tmp_path: Path) -> None:
    """A missing configuration file returns the validation-error code."""
    pipeline_path = tmp_path / "missing.yaml"

    result = runner.invoke(app, ["validate", str(pipeline_path)])

    assert result.exit_code == 3
    assert pipeline_path.name in result.output
    assert "does not exist" in result.output.lower() or "not found" in result.output.lower()
    assert "traceback" not in result.output.lower()


def test_validate_reports_invalid_yaml(tmp_path: Path) -> None:
    """Malformed YAML reports a useful location without a traceback."""
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text("version: [unterminated\n", encoding="utf-8")

    result = runner.invoke(app, ["validate", str(pipeline_path)])

    assert result.exit_code == 3
    assert "yaml" in result.output.lower()
    assert "line" in result.output.lower()
    assert "traceback" not in result.output.lower()


def test_validate_reports_configuration_errors(tmp_path: Path) -> None:
    """Schema errors identify the invalid configuration requirement."""
    pipeline_path = tmp_path / "pipeline.yaml"
    config = _valid_config(tmp_path)
    del config["sink"]
    _write_config(pipeline_path, config)

    result = runner.invoke(app, ["validate", str(pipeline_path)])

    assert result.exit_code == 3
    assert "sink" in result.output.lower()
    assert "missing" in result.output.lower()
    assert "traceback" not in result.output.lower()


def test_validate_does_not_leak_secret_values(tmp_path: Path) -> None:
    """Validation errors never echo sensitive values from YAML."""
    pipeline_path = tmp_path / "pipeline.yaml"
    config = _valid_config(tmp_path)
    secret = "ETLRELAY_TEST_SECRET_SENTINEL_84721"
    config["api_token"] = secret
    _write_config(pipeline_path, config)

    result = runner.invoke(app, ["validate", str(pipeline_path)])

    assert result.exit_code == 3
    assert "api_token" in result.output
    assert secret not in result.output
    assert "traceback" not in result.output.lower()


def test_validate_does_not_open_output_resources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validation does not open output resources or execute the pipeline."""
    pipeline_path = tmp_path / "pipeline.yaml"
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    input_path.write_text("id\n1\n2\n", encoding="utf-8")
    _write_config(pipeline_path, _valid_config(tmp_path))

    def fail_open_write(self: LocalFileSystem, path: str):
        pytest.fail(f"validate attempted to open output resource: {path}")

    monkeypatch.setattr(LocalFileSystem, "open_write", fail_open_write)

    result = runner.invoke(app, ["validate", str(pipeline_path)])

    assert result.exit_code == 0
    assert not output_path.exists()
    assert input_path.read_text(encoding="utf-8") == "id\n1\n2\n"


def test_validate_configuration_error_exits_with_code_3(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report configuration errors as validation failures."""
    pipeline = tmp_path / "pipeline.yml"
    _patch_config_loader_failure(
        monkeypatch,
        ConfigurationError("Pipeline component is invalid."),
    )

    result = CliRunner().invoke(cli.app, ["validate", str(pipeline)])

    assert result.exit_code == 3
    assert "Invalid pipeline configuration" in result.output
    assert "Pipeline component is invalid." in result.output


def test_validate_yaml_error_without_problem_mark_uses_generic_message(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Handle YAML errors that lack source-location information."""
    pipeline = tmp_path / "pipeline.yml"
    _patch_config_loader_failure(
        monkeypatch,
        yaml.YAMLError("internal parser detail"),
    )

    result = CliRunner().invoke(cli.app, ["validate", str(pipeline)])

    assert result.exit_code == 3
    assert "Invalid YAML syntax." in result.output
    assert "internal parser detail" not in result.output


def test_validate_filesystem_error_for_missing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report a missing file when a filesystem operation fails."""
    pipeline = tmp_path / "missing.yml"
    _patch_config_loader_failure(
        monkeypatch,
        FileSystemError("internal filesystem detail"),
    )

    result = CliRunner().invoke(cli.app, ["validate", str(pipeline)])

    assert result.exit_code == 3
    assert "does not exist" in result.output
    assert "internal filesystem detail" not in result.output


def test_validate_filesystem_error_for_existing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report an unreadable file when it exists."""
    pipeline = tmp_path / "pipeline.yml"
    pipeline.write_text("placeholder", encoding="utf-8")
    _patch_config_loader_failure(
        monkeypatch,
        FileSystemError("internal filesystem detail"),
    )

    result = CliRunner().invoke(cli.app, ["validate", str(pipeline)])

    assert result.exit_code == 3
    assert "Unable to read pipeline configuration file" in result.output
    assert "internal filesystem detail" not in result.output


def test_validate_permission_error_uses_specific_message(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report permission failures without exposing the underlying exception."""
    pipeline = tmp_path / "pipeline.yml"
    pipeline.write_text("placeholder", encoding="utf-8")
    _patch_config_loader_failure(
        monkeypatch,
        PermissionError("internal permission detail"),
    )

    result = CliRunner().invoke(cli.app, ["validate", str(pipeline)])

    assert result.exit_code == 3
    assert "Permission denied reading pipeline configuration" in result.output
    assert "internal permission detail" not in result.output


def test_validate_oserror_for_missing_file_reports_missing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report a missing path when an OS error occurs."""
    pipeline = tmp_path / "missing.yml"
    _patch_config_loader_failure(
        monkeypatch,
        OSError("internal OS detail"),
    )

    result = CliRunner().invoke(cli.app, ["validate", str(pipeline)])

    assert result.exit_code == 3
    assert "does not exist" in result.output
    assert "internal OS detail" not in result.output


def test_validate_oserror_for_existing_file_reports_read_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report a generic read failure for an existing file."""
    pipeline = tmp_path / "pipeline.yml"
    pipeline.write_text("placeholder", encoding="utf-8")
    _patch_config_loader_failure(
        monkeypatch,
        OSError("internal OS detail"),
    )

    result = CliRunner().invoke(cli.app, ["validate", str(pipeline)])

    assert result.exit_code == 3
    assert "Unable to read pipeline configuration file" in result.output
    assert "internal OS detail" not in result.output


def test_validate_path_validation_error_is_reported_safely(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Handle path-validation failures as validation errors."""
    pipeline = tmp_path / "pipeline.yml"
    pipeline.write_text("placeholder", encoding="utf-8")
    _patch_config_loader_failure(
        monkeypatch,
        PathValidationError("internal path detail"),
    )

    result = CliRunner().invoke(cli.app, ["validate", str(pipeline)])

    assert result.exit_code == 3
    assert "Unable to read pipeline configuration file" in result.output
    assert "internal path detail" not in result.output


def test_validate_unexpected_error_returns_code_1_without_details(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Hide unexpected internal exception details from CLI output."""
    pipeline = tmp_path / "pipeline.yml"
    pipeline.write_text("placeholder", encoding="utf-8")
    _patch_config_loader_failure(
        monkeypatch,
        RuntimeError("sensitive internal detail"),
    )

    result = CliRunner().invoke(cli.app, ["validate", str(pipeline)])

    assert result.exit_code == 1
    assert "Unexpected error while validating pipeline configuration." in result.output
    assert "sensitive internal detail" not in result.output


def test_run_reports_that_command_is_not_yet_implemented() -> None:
    """Report the temporary run-command placeholder."""
    result = CliRunner().invoke(cli.app, ["run", "pipeline.yml"])

    assert result.exit_code == 1
    assert "The 'run' command is not implemented yet." in result.output
