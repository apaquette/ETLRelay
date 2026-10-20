"""Configuration validation and construction for SQL sinks.

This module provides a factory that constructs SQL sinks using an engine
supplied by the SQL engine provider and a validator for SQL sink configuration.
"""

from collections.abc import Mapping
from typing import Final, cast

from etlrelay.config._validation import (
    as_mapping,
    non_empty_string_error,
    validate_keys,
)
from etlrelay.config.sql_engine_factory import SqlEngineProvider
from etlrelay.sinks.sql import SqlSink


class SqlSinkConfigFactory:
    """Construct SQL sinks from validated configuration mappings.

    The factory obtains an engine from the configured SQL engine provider
    using the name of the environment variable associated with the connection
    URL. Environment-variable resolution and preflight are handled separately
    by the configuration-building lifecycle.
    """

    def __init__(self, engine_factory: SqlEngineProvider) -> None:
        """Initialize the factory with a SQL engine provider.

        Args:
            engine_factory: Provider responsible for supplying SQL engines
                associated with preflighted connection URL references.
        """
        self._engine_factory = engine_factory

    def build(self, config: Mapping[str, object]) -> SqlSink:
        """Build a SQL sink from its configuration.

        Args:
            config: Validated configuration mapping containing
                ``connection_url_env`` and ``table_name``, and optionally
                ``schema``.

        Returns:
            A SqlSink configured with the supplied engine, destination table,
            and optional database schema.

        Note:
            This method assumes configuration validation and SQL environment
            preflight have already succeeded. It does not directly read or
            validate environment variables.
        """
        engine = self._engine_factory.create(cast(str, config["connection_url_env"]))
        return SqlSink(
            engine=engine,
            table_name=cast(str, config["table_name"]),
            schema=cast(str | None, config.get("schema")),
        )


class SqlSinkConfigValidator:
    """Validate configuration mappings for SQL sinks.

    The validator checks supported and required fields, the sink type, the
    connection URL environment-variable name, the destination table name,
    and the optional schema value.
    """

    _ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
        {
            "type",
            "connection_url_env",
            "table_name",
            "schema",
        }
    )
    _REQUIRED_KEYS: Final[frozenset[str]] = frozenset(
        {
            "type",
            "connection_url_env",
            "table_name",
        }
    )

    def validate(self, config: object, path: str) -> list[str]:
        """Validate SQL sink configuration and return any errors.

        The configuration must be a mapping containing ``type``,
        ``connection_url_env``, and ``table_name``. The type must be
        ``"sql"``, and the connection URL environment-variable name and table
        name must be non-empty strings. The optional ``schema`` field, when
        present, must also be a non-empty string.

        Args:
            config: Configuration value to validate.
            path: Configuration path used to identify validation errors.

        Returns:
            A list of validation error messages. The list is empty when
            validation succeeds. If mapping shape, supported keys, or required
            keys are invalid, those errors are returned before the remaining
            field values are checked.
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

        for key in {"connection_url_env", "table_name"}:
            error = non_empty_string_error(mapping[key], f"{path}.{key}")
            if error is not None:
                errors.append(error)

        connection_reference = mapping["connection_url_env"]

        if (
            isinstance(connection_reference, str)
            and connection_reference.strip()
            and not connection_reference.isidentifier()
        ):
            errors.append(f"{path}.connection_url_env must name a valid environment variable.")

        if "schema" in mapping:
            errors.extend(self._validate_schema(mapping, path))

        return errors

    def _validate_schema(self, mapping: Mapping[str, object], path: str) -> list[str]:
        """Validate the optional SQL schema field.

        Args:
            mapping: SQL sink configuration mapping containing ``schema``.
            path: Configuration path used to identify validation errors.

        Returns:
            An empty list if ``schema`` is a non-empty string; otherwise, a
            list containing an error message for the schema field.
        """
        schema = mapping["schema"]
        schema_path = f"{path}.schema"

        if not isinstance(schema, str) or not schema.strip():
            return [f"{schema_path} must be a string."]

        return []
