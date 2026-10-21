"""Rename columns in a batch while preserving their order and schema.

The processor renames columns according to a mapping of existing column
names to new column names. Column order, values, Arrow data types, and
nullability are preserved.

Multiple columns can be renamed simultaneously, including swapping names,
provided that the resulting column names are unique.

Raises:
    ValueError: If a source column does not exist, multiple columns are
        mapped to the same new name, or a new name conflicts with an
        existing column that is not being renamed.
"""

from collections import Counter
from collections.abc import Mapping

import pyarrow as pa

from etlrelay.core import Batch


class RenameColumns:
    def __init__(self, mapping: Mapping[str, str]):
        """Rename columns using a mapping of existing names to new names.

        Column order, values, Arrow data types, and nullability are preserved.
        Multiple columns can be renamed simultaneously, including swapping
        names, provided that the final column names are unique.

        Validation occurs when processing a batch. Unknown source columns,
        duplicate destination names, and conflicts with existing columns
        that are not being renamed raise ValueError.

        Example:
            from etlrelay.processors import RenameColumns

            processor = RenameColumns(mapping={"name": "customer_name"})
            result = processor.process(batch)
        """
        self._mapping = mapping

    def process(self, batch: Batch) -> Batch:
        """Rename columns in a batch.

        Args:
            batch: The batch whose columns will be renamed.

        Returns:
            A new Batch with renamed columns, preserving column order, values,
            data types, and nullability.

        Raises:
            ValueError: If a source column does not exist or the mapping would
                produce duplicate column names.

        """
        table = batch.table

        self._validate_mapping(table)

        table = table.rename_columns(self._mapping)
        return Batch(table)

    def _validate_mapping(self, table: pa.Table) -> None:
        """Validate the mapping against the input table's column names.

        Args:
            table: The PyArrow table whose column names are being validated.

        Raises:
            ValueError: If a source column does not exist, multiple source
                columns map to the same destination name, or a destination
                name conflicts with an existing column that is not being
                renamed.
        """
        existing_columns = set(table.column_names)
        mapping_keys = set(self._mapping)
        mapping_values = set(self._mapping.values())
        missing = mapping_keys - existing_columns

        if missing:
            raise ValueError(f"Column(s) do not exist: {', '.join(sorted(missing))}")

        if len(mapping_values) != len(self._mapping.values()):
            duplicates = [
                item for item, count in Counter(self._mapping.values()).items() if count > 1
            ]
            raise ValueError(f"Duplicate columns are not allowed: {', '.join(sorted(duplicates))}")

        for update_name in self._mapping.values():
            if update_name in existing_columns and update_name not in mapping_keys:
                raise ValueError(f"Column already exists and is not being renamed: {update_name}")

        final_names = [self._mapping.get(name, name) for name in table.column_names]
        duplicates = sorted(name for name, count in Counter(final_names).items() if count > 1)
        if duplicates:
            raise ValueError(f"Duplicate columns are not allowed: {', '.join(duplicates)}")
