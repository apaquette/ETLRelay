from collections.abc import Mapping
from typing import cast

from etlrelay.processors.rename_columns import RenameColumns


class RenameColumnsConfigFactory:
    """Construct a RenameColumns processor from validated configuration."""

    def build(self, config: Mapping[str, object]) -> RenameColumns:
        """Build a processor using the configured column mapping."""
        return RenameColumns(
            mapping=cast(Mapping[str, str], config["mapping"]),
        )
