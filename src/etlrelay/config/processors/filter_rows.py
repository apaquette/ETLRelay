from collections.abc import Mapping
from typing import cast

from etlrelay.processors.filter_rows import FilterRows


class FilterRowsConfigFactory:
    """Construct a FilterRows processor from validated configuration."""

    def build(self, config: Mapping[str, object]) -> FilterRows:
        """Build a processor using the configured predicate."""
        return FilterRows(
            column=cast(str, config["column"]),
            operator=cast(str, config["operator"]),
            value=cast(str | int | float | bool, config["value"]),
        )
