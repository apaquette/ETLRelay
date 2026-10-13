"""Filter rows using Apache Arrow comparison operations.

This module provides the FilterRows processor, which filters a Batch using
a single comparison predicate on a specified column.
"""

from typing import Any

import pyarrow as pa
import pyarrow.compute as pc

from etlrelay.core import Batch


class FilterRows:
    """Filter a batch using a single column comparison predicate.

    Supported operators are ==, !=, <, <=, >, and >=. Comparisons use
    Apache Arrow compute operations without custom casting.

    Rows whose comparison evaluates to false or null are excluded.
    The input schema is preserved, including when no rows match.

    The processor can be reused across batches without retaining
    batch-specific state.

    Example:
        from etlrelay.processors import FilterRows

        processor = FilterRows(column="age", operator=">=", value=18)
        result = processor.process(batch)

    Raises:
        ValueError: If the comparison operator is unsupported.
    """

    operator_map = {
        "==": "equal",
        "!=": "not_equal",
        "<": "less",
        ">": "greater",
        "<=": "less_equal",
        ">=": "greater_equal",
    }

    def __init__(self, column: str, operator: str, value: Any):
        """Initialize the processor with a comparison predicate.

        Args:
            column: Name of the column to compare.
            operator: Comparison operator. Must be one of ==, !=, <, <=,
                >, or >=.
            value: Value to compare against the selected column.

        Raises:
            ValueError: If the operator is unsupported.
        """
        if operator not in self.operator_map.keys():
            raise ValueError(f"Unsupported operator: {operator!r}") from None
        self._column = column
        self._comparison = self.operator_map[operator]
        self._value = value

    def process(self, batch: Batch) -> Batch:
        """Return a batch containing only rows that satisfy the predicate.

        Rows whose comparison evaluates to false or null are excluded.
        The resulting batch preserves the input table's schema.

        Args:
            batch: Batch containing the column to filter.

        Returns:
            A new Batch containing the matching rows, with the original
            schema preserved.

        Raises:
            ValueError: If the specified column does not exist or is
                ambiguous.
            TypeError: If the column and comparison value have incompatible
                types.
        """
        table = batch.table
        col_index = table.schema.get_field_index(self._column)

        if col_index == -1:
            raise ValueError(f"Unknown or ambiguous column: {self._column!r}")

        try:
            mask = pc.call_function(
                self._comparison,
                [table.column(col_index), self._value],
            )
        except (
            pa.ArrowNotImplementedError,
            pa.ArrowTypeError,
            pa.ArrowInvalid,
            TypeError,
        ) as exc:
            raise TypeError(
                f"Incompatible comparison types for column {self._column!r} "
                f"and value {self._value!r}"
            ) from exc

        filtered_table = table.filter(mask, null_selection_behavior="drop")

        return Batch(filtered_table)
