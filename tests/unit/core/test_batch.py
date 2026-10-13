import pyarrow as pa

from etlrelay.core import Batch


class TestBatch:
    def test_preserves_table_values_and_schema(self):
        schema = pa.schema(
            [
                pa.field("name", pa.string(), nullable=False),
                pa.field("age", pa.int64(), nullable=True),
            ]
        )
        expected_rows = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        table = pa.Table.from_pylist(expected_rows, schema=schema)

        batch = Batch(table=table)

        assert batch.table is table
        assert batch.table.to_pylist() == expected_rows
        assert batch.table.schema.names == ["name", "age"]
        assert batch.table.schema.types == [pa.string(), pa.int64()]
        assert [field.nullable for field in batch.table.schema] == [
            False,
            True,
        ]

    def test_preserves_schema_of_zero_row_table(self):
        schema = pa.schema(
            [
                pa.field("record_id", pa.int64(), nullable=False),
                pa.field("description", pa.string(), nullable=True),
            ]
        )
        table = pa.Table.from_pylist([], schema=schema)

        batch = Batch(table=table)

        assert batch.table.num_rows == 0
        assert batch.table.num_columns == 2
        assert batch.table.schema.equals(schema)
        assert batch.table.schema.names == ["record_id", "description"]
        assert batch.table.schema.types == [pa.int64(), pa.string()]
        assert [field.nullable for field in batch.table.schema] == [
            False,
            True,
        ]
