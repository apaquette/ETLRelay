"""Command-line interface for ETLRelay."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, NoReturn, cast

import typer
from typer.core import TyperGroup

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
    _not_implemented_yet("validate")


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
