import pyarrow as pa

from etlrelay.core import Batch
from etlrelay.processors import RenameColumns, SelectColumns


def test_select_columns_then_rename_columns():
    schema = pa.schema(
        [
            pa.field("id", pa.int64(), nullable=False),
            pa.field("name", pa.string(), nullable=False),
            pa.field("department", pa.string(), nullable=False),
        ]
    )
    table = pa.Table.from_pylist(
        [
            {"id": 1, "name": "Ada", "department": "Engineering"},
            {"id": 2, "name": "Sam", "department": "Support"},
        ],
        schema=schema,
    )
    batch = Batch(table=table)

    selected = SelectColumns(columns=["department", "name"]).process(batch)

    result = RenameColumns(mapping={"department": "team"}).process(selected)

    expected_schema = pa.schema(
        [
            pa.field("team", pa.string(), nullable=False),
            pa.field("name", pa.string(), nullable=False),
        ]
    )

    assert result.table.schema.equals(expected_schema)
    assert result.table.to_pylist() == [
        {"team": "Engineering", "name": "Ada"},
        {"team": "Support", "name": "Sam"},
    ]
