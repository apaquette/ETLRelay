import pyarrow as pa
import pytest

from etlrelay.core import Batch
from etlrelay.processors import SelectColumns


def make_batch() -> Batch:
    schema = pa.schema(
        [
            pa.field("id", pa.int64(), nullable=False),
            pa.field("name", pa.string(), nullable=False),
            pa.field("score", pa.float64(), nullable=True),
        ]
    )
    table = pa.Table.from_pylist(
        [
            {"id": 1, "name": "Ada", "score": 91.5},
            {"id": 2, "name": "Sam", "score": None},
            {"id": 3, "name": "Lin", "score": 84.0},
        ],
        schema=schema,
    )
    return Batch(table=table)


class TestSelectColumns:
    def test_selects_single_column(self):
        batch = make_batch()

        result = SelectColumns(columns=["name"]).process(batch)

        expected_schema = pa.schema([pa.field("name", pa.string(), nullable=False)])

        assert isinstance(result, Batch)
        assert result.table.schema.equals(expected_schema)
        assert result.table.to_pylist() == [
            {"name": "Ada"},
            {"name": "Sam"},
            {"name": "Lin"},
        ]

    def test_selects_multiple_columns_in_requested_order(self):
        batch = make_batch()

        result = SelectColumns(columns=["score", "id"]).process(batch)

        expected_schema = pa.schema(
            [
                pa.field("score", pa.float64(), nullable=True),
                pa.field("id", pa.int64(), nullable=False),
            ]
        )

        assert result.table.schema.equals(expected_schema)
        assert result.table.to_pylist() == [
            {"score": 91.5, "id": 1},
            {"score": None, "id": 2},
            {"score": 84.0, "id": 3},
        ]

    def test_rejects_unknown_column(self):
        batch = make_batch()

        with pytest.raises(ValueError, match="missing"):
            SelectColumns(columns=["missing"]).process(batch)

    def test_rejects_duplicate_requested_columns(self):
        batch = make_batch()

        with pytest.raises(ValueError, match="(?i)duplicate"):
            SelectColumns(columns=["id", "id"]).process(batch)

    def test_preserves_schema_when_selecting_from_zero_row_table(self):
        original_schema = pa.schema(
            [
                pa.field("id", pa.int64(), nullable=False),
                pa.field("name", pa.string(), nullable=False),
                pa.field("score", pa.float64(), nullable=True),
            ]
        )
        batch = Batch(table=pa.Table.from_pylist([], schema=original_schema))

        result = SelectColumns(columns=["score", "id"]).process(batch)

        expected_schema = pa.schema(
            [
                pa.field("score", pa.float64(), nullable=True),
                pa.field("id", pa.int64(), nullable=False),
            ]
        )

        assert result.table.num_rows == 0
        assert result.table.schema.equals(expected_schema)
