from collections.abc import Mapping
from typing import cast

from etlrelay.processors.select_columns import SelectColumns


class SelectColumnsConfigFactory:
    """Construct a SelectColumns processor from validated configuration."""

    def build(self, config: Mapping[str, object]) -> SelectColumns:
        """Build a processor using the configured column order."""
        return SelectColumns(
            columns=cast(list[str], config["columns"]),
        )
