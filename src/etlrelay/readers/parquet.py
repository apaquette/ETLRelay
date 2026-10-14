"""Parquet reader implementation for ETLRelay.

This module provides functionality for reading Parquet data from a binary
stream and yielding the parsed data as ETLRelay Batch objects, preserving
the Arrow schema and supported data types.
"""

from collections.abc import Iterable
from typing import BinaryIO

import pyarrow as pa
import pyarrow.parquet as pa_parquet

from etlrelay.core import Batch


class ParquetReader:
    """Read Parquet data from a binary stream and yield ETLRelay batches.

    Preserves the Arrow schema for zero-row Parquet files by yielding an
    empty batch with the file's schema.

    The caller is responsible for managing the stream's lifecycle.

    Raises:
        pyarrow.ArrowInvalid: If the Parquet data is invalid.
        OSError: If an I/O error occurs while reading the stream.
    """

    def read(self, stream: BinaryIO) -> Iterable[Batch]:
        """Read Parquet data from a binary stream and yield batches.

        Args:
            stream: A seekable binary stream containing Parquet data.

        Yields:
            Batches containing the parsed data, one per record batch
            produced by PyArrow. For zero-row files, yields one empty
            batch preserving the file's schema.

        Raises:
            pyarrow.ArrowInvalid: If the Parquet data is invalid.
            OSError: If an I/O error occurs while reading the stream.
        """
        reader = pa_parquet.ParquetFile(stream)

        if reader.metadata.num_rows == 0:
            yield Batch(
                pa.Table.from_batches(
                    [],
                    schema=reader.schema_arrow,
                )
            )
            return

        for record_batch in reader.iter_batches():
            table = pa.Table.from_batches([record_batch])
            yield Batch(table)
