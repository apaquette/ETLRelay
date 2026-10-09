from etlrelay.core.batch import Batch


class TestBatch:
    def test_represents_tabular_data(self):

        batch = Batch(
            table=[
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ]
        )

        expected_output = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]

        assert batch.table == expected_output

    def test_empty_batch(self):
        batch = Batch(table=[])

        expected_output = []

        assert batch.table == expected_output