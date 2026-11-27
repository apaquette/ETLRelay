"""Closed, typed configuration models for SQL sources and sinks.

The models define the bounded YAML contract for SQL components. They are
shared by the leaf validators and component factories so configuration is
validated and materialized consistently before runtime construction.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final, cast

import pyarrow as pa

from etlrelay.config._validation import as_mapping, non_empty_string_error, validate_keys
from etlrelay.sinks.sql import SqlSink
from etlrelay.sources.sql import SqlSource

_ARROW_TYPES: Final[dict[str, pa.DataType]] = {
    "null": pa.null(),
    "bool": pa.bool_(),
    "int8": pa.int8(),
    "int16": pa.int16(),
    "int32": pa.int32(),
    "int64": pa.int64(),
    "uint8": pa.uint8(),
    "uint16": pa.uint16(),
    "uint32": pa.uint32(),
    "uint64": pa.uint64(),
    "float16": pa.float16(),
    "float32": pa.float32(),
    "float64": pa.float64(),
    "string": pa.string(),
    "large_string": pa.large_string(),
    "binary": pa.binary(),
    "large_binary": pa.large_binary(),
    "date32": pa.date32(),
    "date64": pa.date64(),
    "time": pa.time64("us"),
    "timestamp": pa.timestamp("us"),
}


def _rebase_errors(errors: list[str], source_path: str, path: str) -> list[str]:
    """Replace a static component validator's default path with the caller path."""
    prefix = f"{source_path}."
    return [
        f"{path}.{message[len(prefix):]}" if message.startswith(prefix) else message
        for message in errors
    ]


def _parse_arrow_schema(
    value: object,
    path: str,
) -> tuple[pa.Schema | None, list[str]]:
    """Parse the deliberately bounded YAML representation of an Arrow schema.

    YAML supports a mapping containing a non-empty ordered fields list. Each
    field has a non-empty name, one of the supported primitive aliases, and an
    optional Boolean nullable flag (defaulting to true).
    """
    if value is None:
        return None, []

    mapping, errors = as_mapping(value, path)
    if mapping is None:
        return None, errors

    errors.extend(validate_keys(mapping, path, allowed=("fields",), required=("fields",)))
    if errors:
        return None, errors

    raw_fields = mapping["fields"]
    if not isinstance(raw_fields, list) or not raw_fields:
        return None, [f"{path}.fields must be a non-empty list."]

    fields: list[pa.Field] = []
    names: set[str] = set()

    for index, raw_field in enumerate(raw_fields):
        field_path = f"{path}.fields[{index}]"
        field_mapping, field_errors = as_mapping(raw_field, field_path)
        if field_mapping is None:
            errors.extend(field_errors)
            continue

        field_errors.extend(
            validate_keys(
                field_mapping,
                field_path,
                allowed=("name", "type", "nullable"),
                required=("name", "type"),
            )
        )
        if field_errors:
            errors.extend(field_errors)
            continue

        name = field_mapping["name"]
        name_error = non_empty_string_error(name, f"{field_path}.name")
        if name_error is not None:
            errors.append(name_error)
            continue
        assert isinstance(name, str)

        if name in names:
            errors.append(f"{field_path}.name duplicates an earlier schema field: {name!r}.")
            continue

        type_alias = field_mapping["type"]
        if not isinstance(type_alias, str) or type_alias not in _ARROW_TYPES:
            supported = ", ".join(sorted(_ARROW_TYPES))
            errors.append(
                f"{field_path}.type must be one of the supported Arrow type aliases: {supported}."
            )
            continue

        nullable = field_mapping.get("nullable", True)
        if type(nullable) is not bool:
            errors.append(f"{field_path}.nullable must be a Boolean.")
            continue

        names.add(name)
        fields.append(pa.field(name, _ARROW_TYPES[type_alias], nullable=nullable))

    if errors:
        return None, errors

    try:
        return pa.schema(fields), []
    except (TypeError, ValueError, pa.ArrowException) as error:
        return None, [f"{path} could not be constructed as an Arrow schema ({type(error).__name__})."]


@dataclass(frozen=True)
class SqlSourceConfigModel:
    """Validated SQL-source configuration with a materialized Arrow schema."""

    connection_url_env: str
    query: str
    parameters: Mapping[str, Any] | None
    batch_size: int | None
    schema: pa.Schema | None

    @classmethod
    def from_mapping(
        cls,
        config: object,
        path: str,
    ) -> tuple[SqlSourceConfigModel | None, list[str]]:
        """Validate a closed SQL-source mapping and parse its optional schema."""
        mapping, errors = as_mapping(config, path)
        if mapping is None:
            return None, errors

        errors.extend(
            validate_keys(
                mapping,
                path,
                allowed=(
                    "type",
                    "connection_url_env",
                    "query",
                    "parameters",
                    "batch_size",
                    "schema",
                ),
                required=("type", "connection_url_env", "query"),
            )
        )
        if errors:
            return None, errors

        if mapping["type"] != "sql":
            errors.append(f"{path}.type must be 'sql'.")

        connection_reference = mapping["connection_url_env"]
        error = non_empty_string_error(connection_reference, f"{path}.connection_url_env")
        if error is not None:
            errors.append(error)
        elif isinstance(connection_reference, str) and not connection_reference.isidentifier():
            errors.append(
                f"{path}.connection_url_env must name a valid environment variable."
            )

        query = mapping["query"]
        if not isinstance(query, str):
            errors.append(f"{path}.query must be a non-empty string.")
        else:
            errors.extend(_rebase_errors(SqlSource.validate_query(query), "source", path))

        parameters = mapping.get("parameters")
        errors.extend(
            _rebase_errors(SqlSource.validate_parameters(parameters), "source", path)
        )

        batch_size = mapping.get("batch_size")
        errors.extend(
            _rebase_errors(SqlSource.validate_batch_size(batch_size), "source", path)
        )

        arrow_schema, schema_errors = _parse_arrow_schema(
            mapping.get("schema"),
            f"{path}.schema",
        )
        errors.extend(schema_errors)
        if arrow_schema is not None:
            errors.extend(
                _rebase_errors(SqlSource.validate_schema(arrow_schema), "source", path)
            )

        if errors:
            return None, errors

        return (
            cls(
                connection_url_env=cast(str, connection_reference),
                query=cast(str, query),
                parameters=cast(Mapping[str, Any] | None, parameters),
                batch_size=cast(int | None, batch_size),
                schema=arrow_schema,
            ),
            [],
        )


@dataclass(frozen=True)
class SqlSinkConfigModel:
    """Validated SQL-sink configuration."""

    connection_url_env: str
    table_name: str
    schema: str | None

    @classmethod
    def from_mapping(
        cls,
        config: object,
        path: str,
    ) -> tuple[SqlSinkConfigModel | None, list[str]]:
        """Validate a closed SQL-sink mapping."""
        mapping, errors = as_mapping(config, path)
        if mapping is None:
            return None, errors

        errors.extend(
            validate_keys(
                mapping,
                path,
                allowed=("type", "connection_url_env", "table_name", "schema"),
                required=("type", "connection_url_env", "table_name"),
            )
        )
        if errors:
            return None, errors

        if mapping["type"] != "sql":
            errors.append(f"{path}.type must be 'sql'.")

        connection_reference = mapping["connection_url_env"]
        error = non_empty_string_error(connection_reference, f"{path}.connection_url_env")
        if error is not None:
            errors.append(error)
        elif isinstance(connection_reference, str) and not connection_reference.isidentifier():
            errors.append(
                f"{path}.connection_url_env must name a valid environment variable."
            )

        table_name = mapping["table_name"]
        errors.extend(_rebase_errors(SqlSink.validate_table_name(table_name), "sink", path))

        schema = mapping.get("schema")
        errors.extend(_rebase_errors(SqlSink.validate_schema(schema), "sink", path))

        if errors:
            return None, errors

        return (
            cls(
                connection_url_env=cast(str, connection_reference),
                table_name=cast(str, table_name),
                schema=cast(str | None, schema),
            ),
            [],
        )
