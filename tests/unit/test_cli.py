"""Unit tests for the command-line interface."""

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pytest
from typer.testing import CliRunner

import etlrelay.cli as cli
from etlrelay.cli import app

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
