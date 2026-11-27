"""Configuration validation and construction for SQL sinks.

The bounded SQL-sink configuration model is shared by validation and
construction, keeping the YAML component contract explicit and consistent.
"""

from collections.abc import Mapping

from etlrelay.config.sql_engine_factory import SqlEngineProvider
from etlrelay.config.sql_models import SqlSinkConfigModel
from etlrelay.sinks.sql import SqlSink


class SqlSinkConfigFactory:
    """Construct SQL sinks from validated configuration mappings."""

    def __init__(self, engine_factory: SqlEngineProvider) -> None:
        self._engine_factory = engine_factory

    def build(self, config: Mapping[str, object]) -> SqlSink:
        """Build a SQL sink after parsing its bounded configuration model."""
        model, errors = SqlSinkConfigModel.from_mapping(config, "sink")
        if errors or model is None:
            raise ValueError("\n".join(errors))

        engine = self._engine_factory.create(model.connection_url_env)
        return SqlSink(
            engine=engine,
            table_name=model.table_name,
            schema=model.schema,
        )


class SqlSinkConfigValidator:
    """Validate SQL sink configuration through its bounded configuration model."""

    def validate(self, config: object, path: str) -> list[str]:
        """Return path-qualified validation errors without database I/O."""
        _, errors = SqlSinkConfigModel.from_mapping(config, path)
        return errors
