"""CSV serialization for FlowForge batches."""

from pathlib import Path

from flowforge.core.batch import Batch
from flowforge.core.writer import WriterError


class CsvWriter:
    """Serialize FlowForge batches to CSV files.

    The destination CSV file is configured when the writer is created.
    """

    def __init__(self, path: Path):
        """Initialize a CSV writer.

        Args:
            path: The path where CSV files will be written.
        """
        self.path = path

    def write(self, batch: Batch) -> None:
        """Serialize and write a batch to the configured CSV file.

        The batch data is serialized with the first row's keys used as
        the CSV header. The parent directory is created if it does not
        already exist.

        Args:
            batch: The batch containing the data to serialize.

        Raises:
            WriterError: If the batch is empty.
        """
        if not batch.table:
            raise WriterError("Batch is empty. Cannot serialize an empty batch.")

        # Ensure the parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Write the batch data to a CSV file
        with open(self.path, "w", encoding="utf-8") as csv_file:
            # Write header
            headers = batch.table[0].keys()
            csv_file.write(",".join(headers) + "\n")

            # Write rows
            for row in batch.table:
                csv_file.write(",".join(str(row[h]) for h in headers) + "\n")