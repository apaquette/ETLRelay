"""CSV reader implementation for FlowForge.

This module provides functionality for reading CSV data from a binary
stream and yielding the parsed data as FlowForge Batch objects.
"""

from collections.abc import Iterable
from typing import BinaryIO

import pyarrow as pa
import pyarrow.csv as pa_csv

from flowforge.core.batch import Batch


class CsvReader:
    """Read CSV data from a binary stream and yield batches."""

    def read(self, stream: BinaryIO) -> Iterable[Batch]:
        """Read CSV data from a binary stream and yield batches.

        Args:
            stream: A binary stream containing CSV data.

        Yields:
            Batches containing parsed CSV data, one per record batch
            produced by PyArrow's streaming CSV reader.

        Raises:
            pyarrow.ArrowInvalid: If the CSV data cannot be parsed.
            OSError: If an error occurs while reading from the stream.
        """
        reader = pa_csv.open_csv(stream)
        for record_batch in reader:
            table = pa.Table.from_batches([record_batch])
            yield Batch(table)