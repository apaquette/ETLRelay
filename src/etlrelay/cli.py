"""Command-line interface for validating and executing ETLRelay pipelines."""

import logging
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
from etlrelay.readers import YamlDocumentError, YamlReader
from etlrelay.security import PathValidationError, PathValidator
from etlrelay.storage import FileSystemError, LocalFileSystem

logger = logging.getLogger(__name__)

_HELP_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

app = typer.Typer(
    add_completion=False,
    context_settings=_HELP_CONTEXT_SETTINGS,
    help="Run and validate ETLRelay pipelines.",
    invoke_without_command=True,
    no_args_is_help=False,
)


class CliApplication:
    """Coordinate CLI workflows using ETLRelay's existing library services.

    Command execution is separated from Typer registration. Dependencies are
    supplied through factories to support substitution in unit tests.
    """

    def __init__(
        self,
        *,
        component_catalog_factory: Callable[[], Any],
        config_loader_factory: Callable[..., ConfigLoader],
        pipeline_builder_factory: Callable[..., PipelineBuilder],
        version_provider: Callable[[str], str],
    ) -> None:
        """Initialize the application with its service dependencies.

        Args:
            component_catalog_factory: Creates the default component catalog.
            config_loader_factory: Creates a loader for reading and validating
                pipeline configurations.
            pipeline_builder_factory: Creates a builder for constructing
                configured pipelines.
            version_provider: Retrieves installed package version metadata.
        """
        self._component_catalog_factory = component_catalog_factory
        self._config_loader_factory = config_loader_factory
        self._pipeline_builder_factory = pipeline_builder_factory
        self._version_provider = version_provider

    def root_callback(self, ctx: typer.Context) -> None:
        """Display root help when no command is selected.

        Args:
            ctx: Typer context for the root command.

        Raises:
            typer.Exit: With exit code 0 when no subcommand was invoked.
        """
        if ctx.invoked_subcommand is None:
            typer.echo(ctx.get_help())
            raise typer.Exit(code=0)

    def run_pipeline(self, pipeline: Path) -> None:
        """Load, build, and execute a configured pipeline.

        Args:
            pipeline: Path to the YAML pipeline configuration.

        Raises:
            typer.Exit: With exit code 1 for unexpected internal errors,
                3 for configuration or pipeline-build failures, or 4 for
                pipeline execution or resource-cleanup failures.
        """
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
        """Validate a YAML pipeline configuration without executing it.

        Args:
            pipeline: Path to the YAML pipeline configuration.

        Raises:
            typer.Exit: With exit code 1 for unexpected internal errors or
                3 for configuration loading, parsing, or validation failures.
        """
        self._load_configuration(
            pipeline,
            unexpected_error_message=("Unexpected error while validating pipeline configuration."),
        )
        typer.echo(f"Pipeline configuration is valid: {pipeline}")

    def print_version(self) -> None:
        """Print the installed ETLRelay package version.

        Raises:
            typer.Exit: With exit code 1 if package version metadata is
                unavailable.
        """
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
        """Display general CLI help or help for a specific command.

        Args:
            ctx: Typer context for the help command.
            command: Optional command name for which to display help.

        Raises:
            typer.Exit: With exit code 2 if the requested command is unknown.
        """
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
        """Load and validate a pipeline configuration.

        Creates the default component catalog and uses the configured loader
        to parse and validate the YAML file. The same workflow is shared by
        the run and validate commands.

        Args:
            pipeline: Path to the YAML pipeline configuration.
            unexpected_error_message: Diagnostic to display for an
                unexpected error during configuration loading.

        Returns:
            A tuple containing the component catalog and validated pipeline
            configuration.

        Raises:
            typer.Exit: With exit code 1 for unexpected errors or 3 for
                configuration, YAML parsing, filesystem, or path-validation
                failures.
        """
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

        except YamlDocumentError:
            self._exit_validation_error(
                f"Invalid YAML document in '{pipeline}': expected a root mapping with string keys.",
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

        except Exception as error:
            logger.error(
                "Configuration loading failed unexpectedly (%s).",
                type(error).__name__,
            )
            typer.echo(unexpected_error_message, err=True)
            raise typer.Exit(code=1) from None

        return components, validated_config

    @staticmethod
    def _configuration_file_error_message(
        pipeline: Path,
        config_path: Path,
        error: Exception | None = None,
    ) -> str:
        """Build a diagnostic for a configuration file access failure.

        Args:
            pipeline: Original path supplied to the CLI.
            config_path: Expanded and resolved configuration file path.
            error: Optional underlying filesystem or path-related exception.

        Returns:
            A user-facing message distinguishing permission denial, a missing
            file, and another file access failure.
        """
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
        """Build and execute a pipeline and release builder resources.

        Attempts to close the builder after construction or execution,
        including when either operation fails. Reports failures after cleanup
        so cleanup errors do not mask earlier build or execution errors.

        Args:
            pipeline: Original path supplied to the CLI.
            components: Component catalog containing the source, processor,
                and sink registries and SQL engine factory.
            validated_config: Configuration returned by the configuration
                loader.

        Raises:
            typer.Exit: With exit code 1 for unexpected construction errors,
                3 for pipeline-build validation failures, or 4 for execution
                or resource-cleanup failures.
        """
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

            except Exception as error:
                logger.error(
                    "Pipeline construction failed unexpectedly (%s).",
                    type(error).__name__,
                )
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
                except Exception as error:
                    cleanup_failed = True
                    logger.warning(
                        "Pipeline resource cleanup failed (%s).",
                        type(error).__name__,
                    )

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
        """Display a validation error and terminate the command.

        Args:
            message: User-facing validation diagnostic.

        Raises:
            typer.Exit: Always, with exit code 3.
        """
        typer.echo(message, err=True)
        raise typer.Exit(code=3)

    @staticmethod
    def _exit_execution_error(
        pipeline: Path,
        error: Exception,
    ) -> NoReturn:
        """Display a safe execution diagnostic and terminate the command.

        The diagnostic includes the exception type but deliberately omits
        its message to avoid exposing potentially sensitive data.

        Args:
            pipeline: Path to the pipeline that failed.
            error: Exception raised during pipeline execution.

        Raises:
            typer.Exit: Always, with exit code 4.
        """
        typer.echo(
            f"Pipeline execution failed for '{pipeline}' "
            f"({type(error).__name__}). "
            "Check the input data, processor configuration, and output destination. "
            "Exception details were omitted.",
            err=True,
        )
        raise typer.Exit(code=4) from None


def _create_application() -> CliApplication:
    """Create the CLI application with production dependencies.

    Returns:
        A configured application using ETLRelay's default component catalog,
        configuration loader, pipeline builder, and package version provider.
    """
    return CliApplication(
        component_catalog_factory=create_default_component_catalog,
        config_loader_factory=ConfigLoader,
        pipeline_builder_factory=PipelineBuilder,
        version_provider=version,
    )


def _configure_cli_logging(ctx: typer.Context, log_level: str) -> None:
    """Configure ETLRelay logging for the duration of a CLI invocation.

    Logging is written to stderr and restricted to the ETLRelay logger
    hierarchy. Previous logger settings are restored when the root
    command context closes.

    Args:
        ctx: Root Typer context controlling the logging lifecycle.
        log_level: Requested logging level, case-insensitive.

    Raises:
        typer.BadParameter: If the requested level is unsupported.
    """
    level_name = log_level.upper()

    if level_name not in _LOG_LEVELS:
        raise typer.BadParameter(
            "Must be one of: debug, info, warning, error, critical.",
            param_hint="--log-level",
        )

    package_logger = logging.getLogger("etlrelay")

    previous_level = package_logger.level
    previous_propagate = package_logger.propagate

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))

    package_logger.setLevel(_LOG_LEVELS[level_name])
    package_logger.propagate = False
    package_logger.addHandler(handler)

    def restore_logging() -> None:
        package_logger.removeHandler(handler)
        handler.close()
        package_logger.setLevel(previous_level)
        package_logger.propagate = previous_propagate

    ctx.call_on_close(restore_logging)


@app.callback()
def _root_callback(
    ctx: typer.Context,
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            help="Logging verbosity: debug, info, warning, error, or critical.",
        ),
    ] = "warning",
) -> None:
    """Configure logging and display root help when appropriate.

    Args:
        ctx: Typer context for the root command.
        log_level: Minimum severity of ETLRelay log messages.
    """
    _configure_cli_logging(ctx, log_level)
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
    """Execute a pipeline configuration through ETLRelay.

    Args:
        pipeline: Path to the YAML pipeline configuration.

    Raises:
        typer.Exit: With exit code 1 for unexpected internal errors,
            3 for configuration or build failures, or 4 for pipeline
            execution or resource-cleanup failures.
    """
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
    """Validate a pipeline configuration without executing it.

    Args:
        pipeline: Path to the YAML pipeline configuration.

    Raises:
        typer.Exit: With exit code 1 for unexpected internal errors or
            3 for configuration loading, parsing, or validation failures.
    """
    _create_application().validate_pipeline(pipeline)


@app.command(name="version", context_settings=_HELP_CONTEXT_SETTINGS)
def version_command() -> None:
    """Print the installed ETLRelay package version.

    Raises:
        typer.Exit: With exit code 1 if package version metadata is
            unavailable.
    """
    _create_application().print_version()


@app.command(name="help", context_settings=_HELP_CONTEXT_SETTINGS)
def help_command(
    ctx: typer.Context,
    command: Annotated[
        str | None,
        typer.Argument(help="Command to show help for."),
    ] = None,
) -> None:
    """Display help for the CLI or a specific command.

    Args:
        ctx: Typer context for the help command.
        command: Optional command name for which to display help.

    Raises:
        typer.Exit: With exit code 2 if the requested command is unknown.
    """
    _create_application().show_help(ctx, command)


def main() -> None:
    """Launch the ETLRelay command-line application."""
    app()
