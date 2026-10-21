import pyarrow as pa
import pytest

from etlrelay.core import Batch
from etlrelay.processors import RenameColumns


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


class TestRenameColumns:
    @pytest.mark.parametrize("mapping", [{"id": "record_id"}, {"name": "label"}, {}])
    def test_rejects_duplicate_final_names_from_duplicate_input(self, mapping):
        batch = Batch(pa.table([[1], [2], ["Ada"]], names=["id", "id", "name"]))

        with pytest.raises(ValueError, match="Duplicate columns"):
            RenameColumns(mapping=mapping).process(batch)

    def test_renames_single_column(self):
        batch = make_batch()

        result = RenameColumns(mapping={"name": "customer_name"}).process(batch)

        expected_schema = pa.schema(
            [
                pa.field("id", pa.int64(), nullable=False),
                pa.field("customer_name", pa.string(), nullable=False),
                pa.field("score", pa.float64(), nullable=True),
            ]
        )

        assert isinstance(result, Batch)
        assert result.table.schema.equals(expected_schema)
        assert result.table.to_pylist() == [
            {"id": 1, "customer_name": "Ada", "score": 91.5},
            {"id": 2, "customer_name": "Sam", "score": None},
            {"id": 3, "customer_name": "Lin", "score": 84.0},
        ]

    def test_renames_multiple_columns_preserving_field_order(self):
        batch = make_batch()

        result = RenameColumns(mapping={"id": "record_id", "name": "customer_name"}).process(batch)

        expected_schema = pa.schema(
            [
                pa.field("record_id", pa.int64(), nullable=False),
                pa.field("customer_name", pa.string(), nullable=False),
                pa.field("score", pa.float64(), nullable=True),
            ]
        )

        assert result.table.schema.equals(expected_schema)
        assert result.table.to_pylist() == [
            {"record_id": 1, "customer_name": "Ada", "score": 91.5},
            {"record_id": 2, "customer_name": "Sam", "score": None},
            {"record_id": 3, "customer_name": "Lin", "score": 84.0},
        ]

    def test_rejects_unknown_source_column(self):
        batch = make_batch()

        with pytest.raises(ValueError, match="missing"):
            RenameColumns(mapping={"missing": "renamed"}).process(batch)

    def test_rejects_collision_with_unrenamed_column(self):
        batch = make_batch()

        # "score" already exists and is not being renamed.
        with pytest.raises(ValueError, match="score"):
            RenameColumns(mapping={"name": "score"}).process(batch)

    def test_rejects_duplicate_final_names(self):
        batch = make_batch()

        # Two different source columns would receive the same final name.
        with pytest.raises(ValueError, match="label"):
            RenameColumns(mapping={"id": "label", "name": "label"}).process(batch)

    def test_allows_simultaneous_rename_when_final_names_are_unique(self):
        batch = make_batch()

        result = RenameColumns(mapping={"id": "name", "name": "id"}).process(batch)

        expected_schema = pa.schema(
            [
                pa.field("name", pa.int64(), nullable=False),
                pa.field("id", pa.string(), nullable=False),
                pa.field("score", pa.float64(), nullable=True),
            ]
        )

        assert result.table.schema.equals(expected_schema)
        assert result.table.to_pylist() == [
            {"name": 1, "id": "Ada", "score": 91.5},
            {"name": 2, "id": "Sam", "score": None},
            {"name": 3, "id": "Lin", "score": 84.0},
        ]

    def test_preserves_schema_when_renaming_zero_row_table(self):
        original_schema = pa.schema(
            [
                pa.field("id", pa.int64(), nullable=False),
                pa.field("name", pa.string(), nullable=False),
                pa.field("score", pa.float64(), nullable=True),
            ]
        )
        batch = Batch(table=pa.Table.from_pylist([], schema=original_schema))

        result = RenameColumns(mapping={"name": "customer_name"}).process(batch)

        expected_schema = pa.schema(
            [
                pa.field("id", pa.int64(), nullable=False),
                pa.field("customer_name", pa.string(), nullable=False),
                pa.field("score", pa.float64(), nullable=True),
            ]
        )

        assert result.table.num_rows == 0
        assert result.table.schema.equals(expected_schema)
