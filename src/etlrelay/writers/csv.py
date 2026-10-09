"""CSV writer implementation for ETLRelay.

This module provides functionality for serializing ETLRelay Batch objects
as CSV data and writing the serialized data to a binary stream.
"""

from collections.abc import Iterable
from typing import BinaryIO

import pyarrow.csv as pa_csv

from etlrelay.core.batch import Batch


class CsvWriter:
    """Serialize iterable ETLRelay batches as CSV data."""

    def write(self, batches: Iterable[Batch], stream: BinaryIO) -> None:
        """Serialize batches to CSV in the supplied binary stream.

        Writes the CSV header only once, using the first batch's schema.
        Subsequent batches contribute rows without additional headers.

        Args:
            batches: Iterable of batches containing tabular data.
            stream: Writable binary stream that receives the CSV data.

        Raises:
            OSError: If an error occurs while writing to the stream.
        """
        for index, batch in enumerate(batches):
            write_options = pa_csv.WriteOptions(
                include_header=index == 0
            )
            pa_csv.write_csv(
                batch.table,
                stream,
                write_options=write_options,
            )

