"""Batch model for ETLRelay.

This module defines the Batch class, which wraps a PyArrow Table as the
common tabular data representation used throughout ETLRelay's ETL pipeline.
"""

import pyarrow as pa


class Batch:
    """Represent a batch of tabular data using a PyArrow Table.

    Batch provides a consistent data representation for sources, processors,
    and sinks throughout a ETLRelay pipeline.

    Args:
        table: The PyArrow Table containing the batch's data.
    """

    def __init__(self, table: pa.Table) -> None:
        self._table = table

    @property
    def table(self) -> pa.Table:
        """Return the PyArrow Table containing the batch's data.

        Returns:
            The underlying PyArrow Table.
        """
        return self._table