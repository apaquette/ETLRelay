"""Parquet writer implementation for ETLRelay.

This module provides functionality for serializing ETLRelay Batch objects
as Parquet data and writing the serialized output to a caller-provided
binary stream.
"""

from collections.abc import Iterable
from typing import BinaryIO

import pyarrow.parquet as pa_parquet

from etlrelay.core import Batch
from etlrelay.core.writer import WriterError


class ParquetWriter:
    """Serialize ETLRelay batches as Parquet data."""

    def write(self, batches: Iterable[Batch], stream: BinaryIO) -> None:
        """Serialize batches into a single Parquet file.

        Uses the first batch's schema to initialize the Parquet writer.
        Subsequent batches must have a matching schema and are written
        to the same Parquet file.

        Args:
            batches: An iterable of batches containing tabular data.
                At least one batch is required to define the schema.
            stream: A writable binary stream that receives the Parquet
                data. The caller is responsible for managing the
                stream's lifecycle.

        Raises:
            WriterError: If the iterable contains no batches or a batch
                has a schema incompatible with the first batch.
            OSError: If an I/O error occurs while writing to the stream.
        """
        iterator = iter(batches)
        first_batch = next(iterator, None)

        if first_batch is None:
            raise WriterError("Cannot write Parquet without a batch to define the schema.")

        with pa_parquet.ParquetWriter(
            stream,
            schema=first_batch.table.schema,
        ) as writer:
            writer.write_table(first_batch.table)

            for batch in iterator:
                if batch.table.schema != first_batch.table.schema:
                    raise WriterError("Incompatible batch schema")
                writer.write_table(batch.table)
