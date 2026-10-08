"""CSV reader implementation for FlowForge.

This module provides functionality for reading CSV files and converting
their contents into FlowForge Batch objects.
"""

import csv
from pathlib import Path

from flowforge.core.batch import Batch


class CsvReader:
    """Read CSV files and convert their contents into Batch objects."""

    def __init__(self, path: Path):
        """Initialize a CSV reader for the given file.

        Args:
            path: The path to the CSV file to read.
        """
        self.path = path

    def read(self) -> Batch:
        """Read the configured CSV file and return its contents as a Batch.

        The CSV file is read using the standard library CSV parser.
        Each row is represented as a dictionary mapping column names to
        their corresponding values.

        Returns:
            A Batch containing the rows read from the CSV file.

        Raises:
            OSError: If the file cannot be opened or read.
            UnicodeDecodeError: If the file cannot be decoded as UTF-8.
            csv.Error: If the CSV data cannot be parsed.
        """
        data = []
        with open(self.path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                data.append(row)

        return Batch(data)