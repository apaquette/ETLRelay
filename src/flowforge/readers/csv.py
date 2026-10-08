"""CSV reader implementation for FlowForge.

This module provides functionality for reading CSV data from a binary
stream and converting the parsed data into FlowForge Batch objects.
"""

from typing import BinaryIO

import pyarrow.csv as pa_csv

from flowforge.core.batch import Batch


class CsvReader:
    """Read CSV data from a binary stream and convert it into a Batch."""

    def read(self, stream: BinaryIO) -> Batch:
        """Read and parse CSV data from the supplied binary stream.

        Args:
            stream: A binary stream containing CSV data.

        Returns:
            A Batch containing the parsed CSV data.

        Raises:
            pyarrow.ArrowInvalid: If the CSV data cannot be parsed.
            OSError: If an error occurs while reading from the stream.
        """
        table = pa_csv.read_csv(stream)

        return Batch(table)