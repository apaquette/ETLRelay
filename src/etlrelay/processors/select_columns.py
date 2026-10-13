"""Column selection processor for ETLRelay.

This module provides the SelectColumns processor, which selects specific
columns from a Batch while preserving their requested order, values, Arrow
data types, and nullability.
"""

from etlrelay.core import Batch


class SelectColumns:
    """Select specific columns from a batch while preserving their requested order.

    The processor returns a new Batch containing only the selected columns.
    Column values, Arrow data types, and nullability are preserved.

    Raises:
        ValueError: If duplicate column names are provided during
            initialization or a requested column does not exist in the
            input batch.
    """

    def __init__(self, columns: list[str]):
        """Initialize the processor with the columns to select.

        Args:
            columns: Names of the columns to select, in the desired output
                order.

        Raises:
            ValueError: If duplicate column names are provided.
        """
        if len(set(columns)) != len(columns):
            raise ValueError("Duplicate columns not allowed.")

        self._columns = columns

    def process(self, batch: Batch) -> Batch:
        """Select the configured columns from a batch.

        Args:
            batch: The input batch containing the columns to select.

        Returns:
            A new Batch containing only the requested columns in the
            specified order.

        Raises:
            ValueError: If any requested column does not exist in the
                input batch.
        """
        table = batch.table
        missing = set(self._columns) - set(table.column_names)

        if missing:
            raise ValueError(f"Column(s) do not exist: {', '.join(sorted(missing))}")

        return Batch(table.select(self._columns))
