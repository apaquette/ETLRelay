import pyarrow as pa
import pytest

from etlrelay.core import Batch
from etlrelay.processors import FilterRows


def make_batch() -> Batch:
    schema = pa.schema(
        [
            pa.field("id", pa.int64(), nullable=False),
            pa.field("age", pa.int64(), nullable=True),
            pa.field("name", pa.string(), nullable=False),
        ]
    )

    table = pa.Table.from_pylist(
        [
            {"id": 1, "age": 16, "name": "Ada"},
            {"id": 2, "age": 18, "name": "Sam"},
            {"id": 3, "age": 21, "name": "Lin"},
            {"id": 4, "age": None, "name": "Max"},
        ],
        schema=schema,
    )

    return Batch(table=table)


class TestFilterRows:
    @pytest.mark.parametrize(
        ("operator", "value", "expected_ids"),
        [
            ("==", 18, [2]),
            ("!=", 18, [1, 3]),
            ("<", 18, [1]),
            ("<=", 18, [1, 2]),
            (">", 18, [3]),
            (">=", 18, [2, 3]),
        ],
    )
    def test_filters_rows_using_supported_operator(
        self,
        operator: str,
        value: int,
        expected_ids: list[int],
    ):
        batch = make_batch()

        result = FilterRows(
            column="age",
            operator=operator,
            value=value,
        ).process(batch)

        assert isinstance(result, Batch)
        assert result.table.column("id").to_pylist() == expected_ids
        assert result.table.schema.equals(batch.table.schema)

    def test_rejects_unknown_column(self):
        batch = make_batch()

        with pytest.raises(ValueError, match="missing"):
            FilterRows(
                column="missing",
                operator=">=",
                value=18,
            ).process(batch)

    def test_rejects_unsupported_operator(self):
        with pytest.raises(ValueError, match="contains"):
            FilterRows(
                column="age",
                operator="contains",
                value=18,
            )

    def test_rejects_incompatible_comparison_types(self):
        batch = make_batch()

        with pytest.raises(TypeError, match="(?i)(type|compare|incompatible)"):
            FilterRows(
                column="age",
                operator=">",
                value="18",
            ).process(batch)

    def test_excludes_rows_when_comparison_result_is_null(self):
        batch = make_batch()

        result = FilterRows(
            column="age",
            operator=">=",
            value=18,
        ).process(batch)

        assert result.table.column("id").to_pylist() == [2, 3]
        assert None not in result.table.column("id").to_pylist()

    def test_preserves_schema_when_no_rows_match(self):
        batch = make_batch()

        result = FilterRows(
            column="age",
            operator=">",
            value=100,
        ).process(batch)

        assert result.table.num_rows == 0
        assert result.table.schema.equals(batch.table.schema)

    def test_preserves_schema_for_zero_row_input(self):
        original_schema = pa.schema(
            [
                pa.field("id", pa.int64(), nullable=False),
                pa.field("age", pa.int64(), nullable=True),
                pa.field("name", pa.string(), nullable=False),
            ]
        )
        empty_table = pa.Table.from_pylist([], schema=original_schema)
        batch = Batch(table=empty_table)

        result = FilterRows(
            column="age",
            operator=">=",
            value=18,
        ).process(batch)

        assert result.table.num_rows == 0
        assert result.table.schema.equals(original_schema)

    def test_preserves_all_rows_when_all_satisfy_predicate(self):
        batch = make_batch()

        result = FilterRows(
            column="id",
            operator=">=",
            value=1,
        ).process(batch)

        assert result.table.to_pylist() == batch.table.to_pylist()
        assert result.table.schema.equals(batch.table.schema)

    def test_repeated_calls_do_not_retain_batch_state(self):
        processor = FilterRows(
            column="age",
            operator=">=",
            value=18,
        )

        first_batch = Batch(table=pa.table({"age": [17, 25]}))
        second_batch = Batch(table=pa.table({"age": [16, 19]}))

        first_result = processor.process(first_batch)
        second_result = processor.process(second_batch)

        assert first_result.table.to_pylist() == [{"age": 25}]
        assert second_result.table.to_pylist() == [{"age": 19}]
