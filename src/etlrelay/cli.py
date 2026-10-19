"""Command-line interface for ETLRelay."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, NoReturn, cast

import typer
import yaml
from typer.core import TyperGroup

from etlrelay.config.errors import ConfigurationError
from etlrelay.config.loader import ConfigLoader
from etlrelay.default_components import create_default_component_catalog
from etlrelay.readers.yaml import YamlReader
from etlrelay.security.path import PathValidationError, PathValidator
from etlrelay.storage.filesystem import FileSystemError
from etlrelay.storage.local import LocalFileSystem

_HELP_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

app = typer.Typer(
    add_completion=False,
    context_settings=_HELP_CONTEXT_SETTINGS,
    help="Run and validate ETLRelay pipelines.",
    invoke_without_command=True,
    no_args_is_help=False,
)


def _not_implemented_yet(command: str) -> NoReturn:
    """Report an unimplemented command and exit with status 1."""
    typer.echo(
        f"The '{command}' command is not implemented yet.",
        err=True,
    )
    raise typer.Exit(code=1)


@app.callback()
def _root_callback(ctx: typer.Context) -> None:
    """Show the root help when no command is supplied."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)


@app.command(context_settings=_HELP_CONTEXT_SETTINGS)
def run(
    pipeline: Annotated[
        Path,
        typer.Argument(
            metavar="PIPELINE",
            help="Path to the YAML pipeline configuration.",
        ),
    ],
) -> None:
    """Execute the pipeline defined by a YAML configuration file."""
    _not_implemented_yet("run")


def _exit_validation_error(message: str) -> NoReturn:
    """Print a safe validation error and exit with status 3."""
    typer.echo(message, err=True)
    raise typer.Exit(code=3)


@app.command(context_settings=_HELP_CONTEXT_SETTINGS)
def validate(
    pipeline: Annotated[
        Path,
        typer.Argument(
            metavar="PIPELINE",
            help="Path to the YAML pipeline configuration.",
        ),
    ],
) -> None:
    """Validate a YAML pipeline configuration without executing it."""
    config_path = pipeline.expanduser().resolve()

    try:
        components = create_default_component_catalog()
        loader = ConfigLoader(
            LocalFileSystem(
                path_validator=PathValidator(base_path=config_path.parent),
            ),
            YamlReader(),
            components.config_validator,
        )

        loader.load(config_path.name)

    except ConfigurationError as error:
        _exit_validation_error(
            f"Invalid pipeline configuration '{pipeline}': {error}",
        )

    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)

        if mark is None:
            detail = "Invalid YAML syntax."
        else:
            detail = f"Invalid YAML syntax at line {mark.line + 1}, column {mark.column + 1}."

        _exit_validation_error(
            f"{detail} Configuration file: '{pipeline}'.",
        )

    except FileSystemError:
        if not config_path.exists():
            message = f"Pipeline configuration file does not exist: {pipeline}"
        else:
            message = f"Unable to read pipeline configuration file: {pipeline}"

        _exit_validation_error(message)

    except (OSError, PathValidationError) as error:
        if isinstance(error, PermissionError):
            message = f"Permission denied reading pipeline configuration: {pipeline}"
        elif not config_path.exists():
            message = f"Pipeline configuration file does not exist: {pipeline}"
        else:
            message = f"Unable to read pipeline configuration file: {pipeline}"

        _exit_validation_error(message)

    except Exception:
        typer.echo(
            "Unexpected error while validating pipeline configuration.",
            err=True,
        )
        raise typer.Exit(code=1) from None

    typer.echo(f"Pipeline configuration is valid: {pipeline}")


@app.command(name="version", context_settings=_HELP_CONTEXT_SETTINGS)
def version_command() -> None:
    """Print the installed ETLRelay package version."""
    try:
        installed_version = version("etlrelay")
    except PackageNotFoundError:
        typer.echo(
            "Unable to determine the ETLRelay version from installed package metadata.",
            err=True,
        )
        raise typer.Exit(code=1) from None

    typer.echo(f"etlrelay {installed_version}")


@app.command(name="help", context_settings=_HELP_CONTEXT_SETTINGS)
def help_command(
    ctx: typer.Context,
    command: Annotated[
        str | None,
        typer.Argument(help="Command to show help for."),
    ] = None,
) -> None:
    """Show general CLI help or help for a specific command."""
    root_context = ctx.parent
    assert root_context is not None

    if command is None:
        typer.echo(root_context.get_help())
        return

    root_command = cast(TyperGroup, root_context.command)
    target_command = root_command.get_command(root_context, command)
    if target_command is None:
        typer.echo(f"Unknown command '{command}'.", err=True)
        raise typer.Exit(code=2)

    target_context = target_command.make_context(
        command,
        [],
        parent=root_context,
        resilient_parsing=True,
    )
    typer.echo(target_command.get_help(target_context))


def main() -> None:
    """Run the ETLRelay command-line application."""
    app()
