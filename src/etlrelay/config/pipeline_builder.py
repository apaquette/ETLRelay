"""Construct runtime pipelines from validated configuration mappings."""

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
    """Interface needed to preflight and release SQL resources."""

    def preflight(self, references: Mapping[str, str]) -> None:
        """Resolve all referenced environment variables without creating engines."""
        ...

    def close(self) -> None:
        """Dispose engines owned by the factory and discard resolved URLs."""
        ...


class PipelineBuildError(ValueError):
    """Raised when validated configuration cannot be composed into a pipeline."""


class PipelineBuilder:
    """Build a pipeline after resolving all component types and SQL references.

    ``getenv`` is a lightweight fallback for isolated builder use and tests. In
    the default application composition, pass the shared ``SqlEngineFactory``
    so its successful preflight makes resolved URLs available to SQL factories.
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
        self._source_registry = source_registry
        self._sink_registry = sink_registry
        self._processor_registry = processor_registry
        self._getenv: EnvironmentLookup = getenv if getenv is not None else os.environ.get
        self._sql_engine_factory = sql_engine_factory

    def build(self, validated_config: Mapping[str, object]) -> Pipeline:
        """Build a pipeline without executing it or partially building on preflight errors."""
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
        """Release SQL engines owned by this builder's shared engine factory.

        Call after the built pipeline has finished executing. This is a no-op
        when the builder was created without an SQL engine factory.
        """
        if self._sql_engine_factory is not None:
            try:
                self._sql_engine_factory.close()
            except SqlEngineFactoryError as exc:
                raise PipelineBuildError(str(exc)) from None

    @staticmethod
    def _mapping_at(config: Mapping[str, object], section: str) -> Mapping[str, object]:
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
