"""Unit tests for the command-line interface."""

import logging
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import typer
from click._compat import strip_ansi
from typer.testing import CliRunner

import etlrelay.cli as cli
from etlrelay.cli import CliApplication, app

runner = CliRunner()


@pytest.mark.parametrize("args", [[], ["--help"], ["-h"], ["help"]])
def test_root_help_exits_successfully(args: list[str]) -> None:
    result = runner.invoke(app, args)

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "run" in result.output
    assert "validate" in result.output
    assert "version" in result.output


@pytest.mark.parametrize("args", [["--help"], ["-h"]])
@pytest.mark.parametrize("command", ["run", "validate", "version"])
def test_command_help_exits_successfully(
    command: str,
    args: list[str],
) -> None:
    result = runner.invoke(app, [command, *args])

    assert result.exit_code == 0
    assert command in result.output
    assert "Usage:" in result.output


@pytest.mark.parametrize("command", ["run", "validate"])
def test_explicit_command_help(command: str) -> None:
    result = runner.invoke(app, ["help", command])

    assert result.exit_code == 0
    assert command in result.output
    assert "Usage:" in result.output


def test_version_reports_installed_package_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"etlrelay {version('etlrelay')}"


def test_unknown_command_returns_usage_error() -> None:
    result = runner.invoke(app, ["unknown"])

    assert result.exit_code == 2
    assert "unknown" in result.output.lower()
    assert "traceback" not in result.output.lower()


@pytest.mark.parametrize("command", ["run", "validate"])
def test_pipeline_commands_require_a_path(command: str) -> None:
    result = runner.invoke(app, [command])

    assert result.exit_code == 2
    assert "PIPELINE" in result.output
    assert "traceback" not in result.output.lower()


@pytest.mark.parametrize(
    "args",
    [
        ["version", "--invalid"],
        ["run", "--invalid"],
        ["validate", "--invalid"],
    ],
)
def test_invalid_options_return_usage_error(args: list[str]) -> None:
    result = runner.invoke(app, args)

    assert result.exit_code == 2
    assert "traceback" not in result.output.lower()


def test_help_for_unknown_command_returns_usage_error() -> None:
    result = runner.invoke(app, ["help", "unknown"])

    assert result.exit_code == 2
    assert "unknown" in result.output.lower()


def test_console_script_is_registered_in_project_metadata() -> None:
    project_root = Path(__file__).resolve().parents[2]
    pyproject_path = project_root / "pyproject.toml"

    with pyproject_path.open("rb") as file:
        project = tomllib.load(file)

    assert project["project"]["scripts"]["etlrelay"] == "etlrelay.cli:main"


def test_version_handles_missing_package_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_package_not_found(_: str) -> str:
        raise PackageNotFoundError("etlrelay")

    monkeypatch.setattr(cli, "version", raise_package_not_found)

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 1
    assert "Unable to determine the ETLRelay version" in result.output
    assert "Traceback" not in result.output


def test_main_invokes_app(monkeypatch: pytest.MonkeyPatch) -> None:
    invoked = False

    def fake_app() -> None:
        nonlocal invoked
        invoked = True

    monkeypatch.setattr(cli, "app", fake_app)

    cli.main()

    assert invoked


def test_execution_and_cleanup_failures_are_reported_without_secrets(
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    execution_secret = "private-record-value"
    cleanup_secret = "database-password"

    pipeline = Mock()
    pipeline.run.side_effect = RuntimeError(f"Failed processing {execution_secret}")

    builder = Mock()
    builder.build.return_value = pipeline
    builder.close.side_effect = RuntimeError(f"Could not close connection using {cleanup_secret}")

    application = CliApplication(
        component_catalog_factory=Mock(),
        config_loader_factory=Mock(),
        pipeline_builder_factory=Mock(return_value=builder),
        version_provider=Mock(),
    )

    components = SimpleNamespace(
        source_registry=Mock(),
        sink_registry=Mock(),
        processor_registry=Mock(),
        sql_engine_factory=Mock(),
    )

    with caplog.at_level(logging.WARNING, logger="etlrelay.cli"):
        with pytest.raises(typer.Exit) as exc_info:
            application._execute_pipeline(
                pipeline=Path("pipeline.yaml"),
                components=components,
                validated_config={},
            )

    assert exc_info.value.exit_code == 4

    output = capsys.readouterr()
    diagnostics = output.out + output.err + caplog.text

    assert "Pipeline execution failed" in diagnostics
    assert "Pipeline resource cleanup failed" in diagnostics
    assert "RuntimeError" in diagnostics

    assert execution_secret not in diagnostics
    assert cleanup_secret not in diagnostics

    pipeline.run.assert_called_once_with()
    builder.close.assert_called_once_with()


def test_cli_info_logging_outputs_operational_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enable informational logging through the root CLI option."""
    application = Mock()

    def run_pipeline(_pipeline: Path) -> None:
        logger = logging.getLogger("etlrelay.pipeline")
        logger.info("Pipeline execution started.")

    application.run_pipeline.side_effect = run_pipeline
    monkeypatch.setattr(cli, "_create_application", lambda: application)

    result = runner.invoke(
        app,
        ["--log-level", "info", "run", "pipeline.yaml"],
    )

    assert result.exit_code == 0
    assert "Pipeline execution started." in result.stderr
    assert "Pipeline execution started." not in result.stdout

    application.run_pipeline.assert_called_once_with(Path("pipeline.yaml"))


def test_cli_defaults_to_warning_logging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Suppress INFO messages while preserving warnings by default."""
    application = Mock()

    def run_pipeline(_pipeline: Path) -> None:
        logger = logging.getLogger("etlrelay.pipeline")
        logger.info("Informational message.")
        logger.warning("Warning message.")

    application.run_pipeline.side_effect = run_pipeline
    monkeypatch.setattr(cli, "_create_application", lambda: application)

    result = runner.invoke(app, ["run", "pipeline.yaml"])

    assert result.exit_code == 0
    assert "Warning message." in result.stderr
    assert "Informational message." not in result.stderr


@pytest.mark.parametrize(
    ("level", "expected", "suppressed"),
    [
        ("debug", "Debug message.", None),
        ("info", "Info message.", "Debug message."),
        ("warning", "Warning message.", "Info message."),
        ("error", "Error message.", "Warning message."),
        ("critical", "Critical message.", "Error message."),
    ],
)
def test_cli_respects_log_level(
    monkeypatch: pytest.MonkeyPatch,
    level: str,
    expected: str,
    suppressed: str | None,
) -> None:
    """Filter ETLRelay log records according to the configured level."""
    application = Mock()

    def run_pipeline(_pipeline: Path) -> None:
        logger = logging.getLogger("etlrelay.pipeline")
        logger.debug("Debug message.")
        logger.info("Info message.")
        logger.warning("Warning message.")
        logger.error("Error message.")
        logger.critical("Critical message.")

    application.run_pipeline.side_effect = run_pipeline
    monkeypatch.setattr(cli, "_create_application", lambda: application)

    result = runner.invoke(
        app,
        ["--log-level", level, "run", "pipeline.yaml"],
    )

    assert result.exit_code == 0
    assert expected in result.stderr

    if suppressed is not None:
        assert suppressed not in result.stderr


def test_cli_rejects_invalid_log_level() -> None:
    """Reject unsupported log levels as command-line usage errors."""
    result = runner.invoke(
        app,
        ["--log-level", "verbose", "run", "pipeline.yaml"],
    )

    assert result.exit_code == 2

    output = strip_ansi(result.output).lower()
    assert "invalid value" in output


def test_cli_logging_configuration_is_restored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Avoid leaking CLI logging configuration into subsequent invocations."""
    package_logger = logging.getLogger("etlrelay")

    original_handlers = list(package_logger.handlers)
    original_level = package_logger.level
    original_propagate = package_logger.propagate

    application = Mock()

    def run_pipeline(_pipeline: Path) -> None:
        logging.getLogger("etlrelay.pipeline").info("Pipeline execution started.")

    application.run_pipeline.side_effect = run_pipeline
    monkeypatch.setattr(cli, "_create_application", lambda: application)

    for _ in range(2):
        result = runner.invoke(
            app,
            ["--log-level", "info", "run", "pipeline.yaml"],
        )

        assert result.exit_code == 0
        assert result.stderr.count("Pipeline execution started.") == 1

        assert package_logger.handlers == original_handlers
        assert package_logger.level == original_level
        assert package_logger.propagate == original_propagate
