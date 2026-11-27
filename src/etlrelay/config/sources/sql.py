"""Configuration validation and construction for SQL sources.

The bounded SQL-source configuration model is shared by validation and
construction. It keeps the YAML contract separate from the broader Python API,
which can also accept SQLAlchemy Select expressions and native PyArrow schemas.
"""

from collections.abc import Mapping

from etlrelay.config.sql_engine_factory import SqlEngineProvider
from etlrelay.config.sql_models import SqlSourceConfigModel
from etlrelay.sources.sql import SqlSource


class SqlSourceConfigFactory:
    """Construct SQL sources from validated configuration mappings."""

    def __init__(self, engine_factory: SqlEngineProvider) -> None:
        self._engine_factory = engine_factory

    def build(self, config: Mapping[str, object]) -> SqlSource:
        """Build a SQL source after parsing its bounded configuration model."""
        model, errors = SqlSourceConfigModel.from_mapping(config, "source")
        if errors or model is None:
            raise ValueError("\n".join(errors))

        engine = self._engine_factory.create(model.connection_url_env)
        return SqlSource(
            engine=engine,
            query=model.query,
            parameters=model.parameters,
            batch_size=model.batch_size,
            schema=model.schema,
        )


class SqlSourceConfigValidator:
    """Validate SQL source configuration through its bounded configuration model.

    The model restricts YAML to SQL text queries, scalar bind parameters,
    optional positive batch sizes, and a finite declarative Arrow schema format.
    """

    def validate(self, config: object, path: str) -> list[str]:
        """Return path-qualified validation errors without database I/O."""
        _, errors = SqlSourceConfigModel.from_mapping(config, path)
        return errors
