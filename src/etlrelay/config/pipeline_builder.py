"""Construct runtime pipelines from validated configuration mappings.

This module resolves component registrations, preflights SQL environment
references, and constructs runtime pipelines from configuration mappings.
Component factories are invoked only after all component types have been
resolved and SQL environment preflight has succeeded.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Protocol, cast

from etlrelay.config.registry import ComponentRegistration, ComponentRegistry
from etlrelay.config.sql_engine_factory import SqlEngineFactoryError
from etlrelay.core import Processor, Sink, Source
from etlrelay.pipeline import Pipeline

EnvironmentLookup = Callable[[str], str | None]


class SqlEnginePreflighter(Protocol):
    """Define the interface for SQL environment preflight and cleanup.

    Implementations resolve environment-variable references before SQL
    component construction and manage the lifecycle of any SQL engines
    they own.
    """

    def preflight(self, references: Mapping[str, str]) -> None:
        """Resolve referenced environment variables without creating engines.

        Args:
            references: Mapping from configuration paths to environment
                variable names that provide SQL connection URLs.

        Raises:
            SqlEngineFactoryError: If a referenced environment variable
                cannot be resolved or validated.
        """
        ...

    def close(self) -> None:
        """Release owned SQL engines and discard resolved connection URLs.

        Raises:
            SqlEngineFactoryError: If the implementation encounters an error
                while releasing its SQL resources.
        """
        ...


class PipelineBuildError(ValueError):
    """Raised when configuration cannot be composed into a runtime pipeline.

    This exception represents structural, component-resolution, and
    configuration-preflight failures encountered while building a pipeline.
    """


class PipelineBuilder:
    """Build runtime pipelines from validated configuration mappings.

    The builder resolves source, processor, and sink registrations before
    invoking component factories. SQL environment references are preflighted
    before component construction to prevent missing or empty environment
    variables from causing partial pipeline construction.

    ``getenv`` provides a lightweight environment lookup for isolated builder
    use and tests. In the default application composition, the shared
    ``SqlEngineFactory`` should be supplied so successful preflight makes
    resolved connection URLs available to SQL component factories.

    The builder does not execute the pipeline it constructs. When a shared
    SQL engine factory is supplied, the caller is responsible for closing
    the builder after pipeline execution to release the factory's resources.
    """

    def __init__(
        self,
        source_registry: ComponentRegistry[Source],
        sink_registry: ComponentRegistry[Sink],
        processor_registry: ComponentRegistry[Processor],
        getenv: EnvironmentLookup | None = None,
        *,
        sql_engine_factory: SqlEnginePreflighter | None = None,
    ) -> None:
        """Initialize the builder with component registries and SQL preflight.

        Args:
            source_registry: Registry of source component registrations.
            sink_registry: Registry of sink component registrations.
            processor_registry: Registry of processor component registrations.
            getenv: Optional environment-variable lookup function. Defaults to
                ``os.environ.get`` when omitted.
            sql_engine_factory: Optional shared SQL engine factory interface
                used to preflight connection references and release SQL
                resources. When omitted, the builder uses ``getenv`` to
                preflight the required environment variables without managing
                SQL engine resources itself.
        """
        self._source_registry = source_registry
        self._sink_registry = sink_registry
        self._processor_registry = processor_registry
        self._getenv: EnvironmentLookup = getenv if getenv is not None else os.environ.get
        self._sql_engine_factory = sql_engine_factory

    def build(self, validated_config: Mapping[str, object]) -> Pipeline:
        """Construct a pipeline from a validated configuration mapping.

        The builder resolves the source, sink, and all processor registrations
        before performing SQL environment preflight. Only after these steps
        succeed does it invoke component factories and construct the pipeline.
        Processors are constructed in their configured order.

        The returned pipeline is not executed. If component construction fails
        after SQL resources have been acquired during this attempt, the shared
        SQL engine factory is closed before the original exception is
        propagated.

        Args:
            validated_config: Configuration mapping that has already passed
                configuration validation.

        Returns:
            A constructed ``Pipeline`` containing the configured source,
            processors, and sink.

        Raises:
            PipelineBuildError: If required configuration sections are
                malformed, processor configurations are not mappings,
                component types are invalid or unregistered, SQL connection
                references are malformed, or SQL environment preflight fails.
            Exception: Exceptions raised by component factories or pipeline
                construction propagate to the caller. If construction fails
                after SQL preflight and resource acquisition, cleanup is
                attempted before the original exception is re-raised.
        """
        source_config = self._mapping_at(validated_config, "source")
        sink_config = self._mapping_at(validated_config, "sink")
        processors_config = validated_config.get("processors")
        if not isinstance(processors_config, list):
            raise PipelineBuildError("'processors' must be a list in validated configuration.")

        # Resolve every registration before environment preflight or construction.
        source_registration = self._resolve_registration(
            self._source_registry, source_config, "source"
        )
        sink_registration = self._resolve_registration(self._sink_registry, sink_config, "sink")
        processor_registrations: list[ComponentRegistration[Processor]] = []
        processor_configs: list[Mapping[str, object]] = []
        for index, raw_processor_config in enumerate(processors_config):
            path = f"processors[{index}]"
            if not isinstance(raw_processor_config, Mapping):
                raise PipelineBuildError(f"{path} must be a mapping.")
            processor_config = cast(Mapping[str, object], raw_processor_config)
            processor_configs.append(processor_config)
            processor_registrations.append(
                self._resolve_registration(self._processor_registry, processor_config, path)
            )

        references = self._sql_environment_references(
            source_config=source_config,
            sink_config=sink_config,
        )
        self._preflight_sql_environment(references)

        # No component factory is invoked until all types and SQL environment
        # references have passed preflight. If construction fails after a SQL
        # engine has been created, release engines acquired during this attempt.
        try:
            source = source_registration.factory.build(source_config)
            processors = [
                registration.factory.build(processor_config)
                for registration, processor_config in zip(
                    processor_registrations, processor_configs, strict=True
                )
            ]
            sink = sink_registration.factory.build(sink_config)
            return Pipeline(source, processors, sink)
        except Exception:
            if references and self._sql_engine_factory is not None:
                try:
                    self._sql_engine_factory.close()
                except Exception:
                    # Preserve the original construction failure.
                    pass
            raise

    def close(self) -> None:
        """Release SQL resources owned by the shared engine factory.

        Call this method after the built pipeline has finished executing.
        It does not close the pipeline's source, processors, or sink directly.
        When no SQL engine factory was supplied, this method does nothing.

        Raises:
            PipelineBuildError: If the SQL engine factory raises
                ``SqlEngineFactoryError`` while releasing its resources.
        """
        if self._sql_engine_factory is not None:
            try:
                self._sql_engine_factory.close()
            except SqlEngineFactoryError as exc:
                raise PipelineBuildError(str(exc)) from None

    @staticmethod
    def _mapping_at(config: Mapping[str, object], section: str) -> Mapping[str, object]:
        """Retrieve a required mapping-valued configuration section.

        Args:
            config: Configuration mapping containing the requested section.
            section: Name of the section to retrieve.

        Returns:
            The section value as a mapping.

        Raises:
            PipelineBuildError: If the section is missing or its value is not
                a mapping.
        """
        value = config.get(section)
        if not isinstance(value, Mapping):
            raise PipelineBuildError(f"'{section}' must be a mapping in validated configuration.")
        return cast(Mapping[str, object], value)

    @staticmethod
    def _resolve_registration[T](
        registry: ComponentRegistry[T],
        config: Mapping[str, object],
        path: str,
    ) -> ComponentRegistration[T]:
        """Resolve a component registration from its configuration type.

        Args:
            registry: Registry containing the component registrations.
            config: Component configuration mapping with a ``type`` field.
            path: Configuration path used to identify errors.

        Returns:
            The registration associated with the configured component type.

        Raises:
            PipelineBuildError: If the ``type`` field is missing, is not a
                non-empty string, or does not identify a registered component.
        """
        component_type = config.get("type")
        if not isinstance(component_type, str) or not component_type.strip():
            raise PipelineBuildError(f"{path}.type must be a non-empty component type.")
        try:
            return registry.get(component_type)
        except KeyError:
            raise PipelineBuildError(
                f"Unsupported component type '{component_type}' at {path}.type."
            ) from None

    @staticmethod
    def _sql_environment_references(
        *,
        source_config: Mapping[str, object],
        sink_config: Mapping[str, object],
    ) -> dict[str, str]:
        """Collect SQL connection environment-variable references.

        Inspects the source and sink configurations and collects the
        environment-variable names required by components whose type is
        ``sql``. This method identifies references but does not resolve
        environment variables or create SQL engines.

        Args:
            source_config: Source component configuration.
            sink_config: Sink component configuration.

        Returns:
            A mapping from configuration paths to the names of their required
            environment variables. Non-SQL components produce no entries.

        Raises:
            PipelineBuildError: If a SQL source or sink does not specify a
                non-empty ``connection_url_env`` value.
        """
        references: dict[str, str] = {}
        for path, component_config in (
            ("source", source_config),
            ("sink", sink_config),
        ):
            if component_config.get("type") != "sql":
                continue
            variable_name = component_config.get("connection_url_env")
            if not isinstance(variable_name, str) or not variable_name.strip():
                raise PipelineBuildError(
                    f"{path}.connection_url_env must name a non-empty environment variable."
                )
            references[f"{path}.connection_url_env"] = variable_name
        return references

    def _preflight_sql_environment(self, references: Mapping[str, str]) -> None:
        """Resolve and validate SQL environment references before construction.

        When a shared SQL engine factory is configured, delegates preflight to
        that factory. Otherwise, uses the configured environment lookup,
        resolving each unique environment variable at most once. Environment
        lookup exceptions in the fallback path are treated as missing values.
        Connection URL values are never included in validation error messages.

        Args:
            references: Mapping from configuration paths to required
                environment-variable names.

        Raises:
            PipelineBuildError: If a referenced variable is missing or empty,
                or if the shared factory raises ``SqlEngineFactoryError``
                during preflight.
        """
        if not references:
            return

        if self._sql_engine_factory is not None:
            try:
                self._sql_engine_factory.preflight(references)
            except SqlEngineFactoryError as exc:
                # SqlEngineFactory guarantees its errors do not contain resolved URLs.
                raise PipelineBuildError(str(exc)) from None
            return

        # Fallback for tests or callers using factories that do not own a shared
        # SqlEngineFactory. Read each unique variable once and never include its value
        # in an exception message.
        values: dict[str, str | None] = {}
        errors: list[str] = []
        for path, variable_name in references.items():
            if variable_name not in values:
                try:
                    value = self._getenv(variable_name)
                except Exception:
                    value = None
                values[variable_name] = value if isinstance(value, str) and value.strip() else None
            if values[variable_name] is None:
                errors.append(
                    f"{path} references missing or empty environment variable '{variable_name}'."
                )
        if errors:
            raise PipelineBuildError(
                "SQL environment preflight failed:\n - " + "\n - ".join(errors)
            )
