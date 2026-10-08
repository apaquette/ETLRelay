"""CSV writer implementation for FlowForge.

This module provides functionality for serializing FlowForge Batch objects
as CSV data and writing the serialized data to a binary stream.
"""

from typing import BinaryIO

import pyarrow.csv as pa_csv

from flowforge.core.batch import Batch
from flowforge.core.writer import WriterError


class CsvWriter:
    """Serialize FlowForge Batch objects as CSV data."""

    def write(self, batch: Batch, stream: BinaryIO) -> None:
        """Serialize a batch as CSV data and write it to the supplied stream.

        Args:
            batch: The Batch containing tabular data to serialize.
            stream: A binary stream that receives the serialized CSV data.

        Raises:
            WriterError: If the batch contains no rows.
            OSError: If an error occurs while writing to the stream.
        """
        if batch.table.num_rows == 0:
            raise WriterError(
                "Batch is empty. Cannot serialize an empty batch."
            )

        pa_csv.write_csv(batch.table, stream)