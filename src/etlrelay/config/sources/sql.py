"""Configuration validation and construction for SQL sources.

This module provides a factory for constructing SQL sources using a supplied
SQL engine provider and a validator for checking SQL source configuration,
including connection references, query text, and optional query parameters.
"""

from collections.abc import Mapping
from typing import Any, Final, cast

from etlrelay.config._validation import (
    as_mapping,
    non_empty_string_error,
    validate_keys,
)
from etlrelay.config.sql_engine_factory import SqlEngineProvider
from etlrelay.sources.sql import SqlSource


class SqlSourceConfigFactory:
    """Construct SQL sources from validated configuration mappings.

    The factory obtains an engine from the configured SQL engine provider
    using the environment-variable name associated with the connection URL.
    SQL environment-variable resolution and preflight are handled separately
    by the configuration-building lifecycle.
    """

    def __init__(self, engine_factory: SqlEngineProvider) -> None:
        """Initialize the factory with a SQL engine provider.

        Args:
            engine_factory: Provider responsible for supplying SQL engines
                associated with preflighted connection URL references.
        """
        self._engine_factory = engine_factory

    def build(self, config: Mapping[str, object]) -> SqlSource:
        """Build a SQL source from its configuration.

        Args:
            config: Validated configuration mapping containing
                ``connection_url_env`` and ``query``, and optionally
                ``parameters``.

        Returns:
            A SqlSource configured with the supplied engine, query, and
            optional query parameters.

        Note:
            This method assumes configuration validation and SQL environment
            preflight have already succeeded. It does not directly read or
            validate environment variables.
        """
        engine = self._engine_factory.create(cast(str, config["connection_url_env"]))
        return SqlSource(
            engine=engine,
            query=cast(str, config["query"]),
            parameters=cast(
                Mapping[str, Any] | None,
                config.get("parameters"),
            ),
        )


class SqlSourceConfigValidator:
    """Validate SQL source configuration without performing database I/O.

    The validator checks supported and required fields, the source type,
    the connection environment-variable reference, the query string, and
    optional query parameters. Parameter values are restricted to supported
    scalar types or ``None``.
    """

    _ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
        {
            "type",
            "connection_url_env",
            "query",
            "parameters",
        }
    )

    _REQUIRED_KEYS: Final[frozenset[str]] = frozenset(
        {
            "type",
            "connection_url_env",
            "query",
        }
    )

    _SCALAR_TYPES: Final[tuple[type, ...]] = (str, int, float, bool)

    def validate(self, config: object, path: str) -> list[str]:
        """Validate SQL source configuration and return any errors.

        The configuration must be a mapping containing ``type``,
        ``connection_url_env``, and ``query``. The type must be ``"sql"``,
        and the connection environment-variable name and query must be
        non-empty strings. The optional ``parameters`` field must be a
        mapping with string keys and values that are strings, integers,
        floats, booleans, or ``None``.

        Args:
            config: Configuration value to validate.
            path: Configuration path used to identify validation errors.

        Returns:
            A list of validation error messages. The list is empty when
            validation succeeds. If the configuration mapping, supported
            keys, or required keys are invalid, those errors are returned
            before the remaining field values are checked.

        Note:
            This method validates configuration structure and value types.
            It does not resolve connection environment variables, create
            SQL engines, or execute the configured query.
        """
        mapping, errors = as_mapping(config, path)
        if mapping is None:
            return errors

        errors.extend(
            validate_keys(
                mapping,
                path,
                allowed=tuple(self._ALLOWED_KEYS),
                required=tuple(self._REQUIRED_KEYS),
            )
        )

        if errors:
            return errors

        if mapping["type"] != "sql":
            errors.append(f"{path}.type must be 'sql'.")

        for key in {"connection_url_env", "query"}:
            error = non_empty_string_error(mapping[key], f"{path}.{key}")
            if error is not None:
                errors.append(error)

        if "parameters" in mapping:
            errors.extend(self._validate_parameters(mapping, path))

        return errors

    def _validate_parameters(self, mapping: Mapping[str, object], path: str) -> list[str]:
        """Validate SQL query parameters.

        Parameters must be supplied as a mapping with string keys. Values may
        be strings, integers, floats, booleans, or ``None``.

        Args:
            mapping: SQL source configuration mapping containing
                ``parameters``.
            path: Configuration path used to identify validation errors.

        Returns:
            A list of validation error messages. The list is empty when all
            parameter names and values satisfy the required types.
        """
        errors = []
        parameters_path = f"{path}.parameters"

        if not isinstance(mapping["parameters"], Mapping):
            errors.append(f"{parameters_path} must be a mapping.")
            return errors

        for name, value in mapping["parameters"].items():
            if not isinstance(name, str):
                errors.append(f"{parameters_path} keys must be strings.")
                continue

            if value is not None and type(value) not in self._SCALAR_TYPES:
                errors.append(
                    f"{parameters_path}.{name} must be a scalar "
                    "string, integer, float, boolean, or null."
                )

        return errors
