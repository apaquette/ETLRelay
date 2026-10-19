"""Command-line interface for ETLRelay."""

from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, Any, NoReturn, cast

import typer
import yaml
from typer.core import TyperGroup

from etlrelay.config.errors import ConfigurationError
from etlrelay.config.loader import ConfigLoader
from etlrelay.config.pipeline_builder import PipelineBuilder, PipelineBuildError
from etlrelay.default_components import create_default_component_catalog
from etlrelay.pipeline import Pipeline
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


class CliApplication:
    """Handle ETLRelay CLI commands and present their outcomes."""

    def __init__(
        self,
        *,
        component_catalog_factory: Callable[[], Any],
        config_loader_factory: Callable[..., ConfigLoader],
        pipeline_builder_factory: Callable[..., PipelineBuilder],
        version_provider: Callable[[str], str],
    ) -> None:
        """Initialize the application with its service dependencies."""
        self._component_catalog_factory = component_catalog_factory
        self._config_loader_factory = config_loader_factory
        self._pipeline_builder_factory = pipeline_builder_factory
        self._version_provider = version_provider

    def root_callback(self, ctx: typer.Context) -> None:
        """Show root help when no command is supplied."""
        if ctx.invoked_subcommand is None:
            typer.echo(ctx.get_help())
            raise typer.Exit(code=0)

    def run_pipeline(self, pipeline: Path) -> None:
        """Load, build, and execute a configured pipeline."""
        components, validated_config = self._load_configuration(
            pipeline,
            unexpected_error_message=("Unexpected error while loading pipeline configuration."),
        )

        self._execute_pipeline(
            pipeline=pipeline,
            components=components,
            validated_config=validated_config,
        )

        typer.echo(f"Pipeline completed: {pipeline}")

    def validate_pipeline(self, pipeline: Path) -> None:
        """Validate a YAML pipeline configuration without executing it."""
        self._load_configuration(
            pipeline,
            unexpected_error_message=("Unexpected error while validating pipeline configuration."),
        )
        typer.echo(f"Pipeline configuration is valid: {pipeline}")

    def print_version(self) -> None:
        """Print the installed ETLRelay package version."""
        try:
            installed_version = self._version_provider("etlrelay")
        except PackageNotFoundError:
            typer.echo(
                "Unable to determine the ETLRelay version from installed package metadata.",
                err=True,
            )
            raise typer.Exit(code=1) from None

        typer.echo(f"etlrelay {installed_version}")

    def show_help(
        self,
        ctx: typer.Context,
        command: str | None = None,
    ) -> None:
        """Show root help or help for a specific command."""
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

    def _load_configuration(
        self,
        pipeline: Path,
        *,
        unexpected_error_message: str,
    ) -> tuple[Any, Any]:
        """Load and validate a pipeline configuration using library services."""
        config_path = pipeline.expanduser().resolve()

        try:
            components = self._component_catalog_factory()
            loader = self._config_loader_factory(
                LocalFileSystem(
                    path_validator=PathValidator(base_path=config_path.parent),
                ),
                YamlReader(),
                components.config_validator,
            )
            validated_config = loader.load(config_path.name)

        except ConfigurationError as error:
            self._exit_validation_error(
                f"Invalid pipeline configuration '{pipeline}': {error}",
            )

        except yaml.YAMLError as error:
            mark = getattr(error, "problem_mark", None)
            if mark is None:
                detail = "Invalid YAML syntax."
            else:
                detail = f"Invalid YAML syntax at line {mark.line + 1}, column {mark.column + 1}."

            self._exit_validation_error(
                f"{detail} Configuration file: '{pipeline}'.",
            )

        except FileSystemError:
            self._exit_validation_error(
                self._configuration_file_error_message(
                    pipeline,
                    config_path,
                ),
            )

        except (OSError, PathValidationError) as error:
            self._exit_validation_error(
                self._configuration_file_error_message(
                    pipeline,
                    config_path,
                    error,
                ),
            )

        except Exception:
            typer.echo(unexpected_error_message, err=True)
            raise typer.Exit(code=1) from None

        return components, validated_config

    @staticmethod
    def _configuration_file_error_message(
        pipeline: Path,
        config_path: Path,
        error: Exception | None = None,
    ) -> str:
        """Create an actionable message for configuration file access errors."""
        if isinstance(error, PermissionError):
            return f"Permission denied reading pipeline configuration: {pipeline}"

        if not config_path.exists():
            return f"Pipeline configuration file does not exist: {pipeline}"

        return f"Unable to read pipeline configuration file: {pipeline}"

    def _execute_pipeline(
        self,
        *,
        pipeline: Path,
        components: Any,
        validated_config: Any,
    ) -> None:
        """Build and execute a pipeline, closing runtime resources afterward."""
        builder: PipelineBuilder | None = None
        execution_pipeline: Pipeline | None = None
        build_error: PipelineBuildError | None = None
        unexpected_build_failure = False
        execution_error: Exception | None = None
        cleanup_failed = False

        try:
            try:
                builder = self._pipeline_builder_factory(
                    source_registry=components.source_registry,
                    sink_registry=components.sink_registry,
                    processor_registry=components.processor_registry,
                    sql_engine_factory=components.sql_engine_factory,
                )
                execution_pipeline = builder.build(validated_config)

            except PipelineBuildError as error:
                build_error = error

            except Exception:
                unexpected_build_failure = True

            if execution_pipeline is not None:
                try:
                    execution_pipeline.run()
                except Exception as error:
                    execution_error = error

        finally:
            if builder is not None:
                try:
                    builder.close()
                except Exception:
                    cleanup_failed = True

        # Report failures after cleanup to avoid masking the primary error.
        if build_error is not None:
            self._exit_validation_error(
                f"Unable to build pipeline from configuration '{pipeline}': {build_error}",
            )

        if unexpected_build_failure:
            typer.echo(
                "Unexpected error while constructing the pipeline.",
                err=True,
            )
            raise typer.Exit(code=1) from None

        if execution_error is not None:
            self._exit_execution_error(pipeline, execution_error)

        if cleanup_failed:
            typer.echo(
                f"Pipeline '{pipeline}' completed, but runtime resource cleanup failed.",
                err=True,
            )
            raise typer.Exit(code=4) from None

    @staticmethod
    def _exit_validation_error(message: str) -> NoReturn:
        """Print a validation error and exit with status 3."""
        typer.echo(message, err=True)
        raise typer.Exit(code=3)

    @staticmethod
    def _exit_execution_error(
        pipeline: Path,
        error: Exception,
    ) -> NoReturn:
        """Report a safe pipeline execution error and exit with status 4."""
        typer.echo(
            f"Pipeline execution failed for '{pipeline}' "
            f"({type(error).__name__}). "
            "Check the input data, processor configuration, and output destination. "
            "Exception details were omitted.",
            err=True,
        )
        raise typer.Exit(code=4) from None


def _create_application() -> CliApplication:
    """Compose the CLI application with the production dependencies."""
    return CliApplication(
        component_catalog_factory=create_default_component_catalog,
        config_loader_factory=ConfigLoader,
        pipeline_builder_factory=PipelineBuilder,
        version_provider=version,
    )


# Typer adapters. Keep these functions minimal; command logic belongs to the
# application class.
@app.callback()
def _root_callback(ctx: typer.Context) -> None:
    """Show root help when no command is supplied."""
    _create_application().root_callback(ctx)


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
    _create_application().run_pipeline(pipeline)


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
    _create_application().validate_pipeline(pipeline)


@app.command(name="version", context_settings=_HELP_CONTEXT_SETTINGS)
def version_command() -> None:
    """Print the installed ETLRelay package version."""
    _create_application().print_version()


@app.command(name="help", context_settings=_HELP_CONTEXT_SETTINGS)
def help_command(
    ctx: typer.Context,
    command: Annotated[
        str | None,
        typer.Argument(help="Command to show help for."),
    ] = None,
) -> None:
    """Show general CLI help or help for a specific command."""
    _create_application().show_help(ctx, command)


def main() -> None:
    """Run the command-line application."""
    app()
