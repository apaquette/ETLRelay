"""Unit tests for the SQL source."""

from collections.abc import Generator, Mapping, Sequence
from typing import Any
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import OperationalError

from etlrelay.core import Batch
from etlrelay.sources.sql import SqlSource


class TestSqlSource:
    @pytest.fixture
    def sqlalchemy_mocks(self):
        """Provide a mocked engine, connection, and connection context."""
        engine = MagicMock()
        connection_context = MagicMock()
        connection_context.__exit__.return_value = False

        connection = MagicMock()
        connection_context.__enter__.return_value = connection
        engine.connect.return_value = connection_context

        return engine, connection, connection_context

    def make_result(
        self,
        columns: list[str],
        rows: list[dict[str, object]],
    ) -> MagicMock:
        """Create a mocked SQLAlchemy result."""
        result = MagicMock()
        result.keys.return_value = columns
        result.mappings.return_value = rows
        return result

    def test_read_executes_query_and_returns_one_batch(self, sqlalchemy_mocks) -> None:
        """Execute the parameterized query and convert its rows to a batch."""
        engine, connection, connection_context = sqlalchemy_mocks
        query = "SELECT id, name FROM customers WHERE id > :minimum_id"
        parameters = {"minimum_id": 1}
        statement = object()
        result = self.make_result(
            ["id", "name"],
            [
                {"id": 2, "name": "Alice"},
                {"id": 3, "name": "Bob"},
            ],
        )
        connection.execute.return_value = result

        source = SqlSource(engine, query, parameters=parameters)

        with patch("etlrelay.sources.sql.text", return_value=statement) as text_mock:
            batches = list(source.read())

        text_mock.assert_called_once_with(query)
        connection.execute.assert_called_once_with(statement, parameters)

        assert len(batches) == 1
        assert isinstance(batches[0], Batch)
        assert batches[0].table.to_pylist() == [
            {"id": 2, "name": "Alice"},
            {"id": 3, "name": "Bob"},
        ]

        result.close.assert_called_once_with()
        connection_context.__exit__.assert_called_once_with(None, None, None)
        engine.dispose.assert_not_called()

    def test_read_returns_no_batches_for_empty_result(self, sqlalchemy_mocks) -> None:
        """Return an empty iterable when the query returns no rows."""
        engine, connection, connection_context = sqlalchemy_mocks
        result = self.make_result(["id", "name"], [])
        connection.execute.return_value = result

        source = SqlSource(engine, "SELECT id, name FROM customers")

        batches = list(source.read())
        assert batches == []
        result.close.assert_called_once_with()
        connection_context.__exit__.assert_called_once_with(None, None, None)

    def test_read_rejects_duplicate_result_column_names(
        self,
        sqlalchemy_mocks,
    ) -> None:
        """Raise ValueError when SQL results contain duplicate column names."""
        engine, connection, connection_context = sqlalchemy_mocks
        result = self.make_result(["id", "id"], [])
        connection.execute.return_value = result

        source = SqlSource(engine, "SELECT id, id FROM customers")

        with pytest.raises(ValueError, match="duplicate column names"):
            source.read()

        result.mappings.assert_not_called()
        result.close.assert_called_once_with()

        assert connection_context.__exit__.call_args.args[0] is ValueError

    def test_read_propagates_query_execution_errors(self, sqlalchemy_mocks) -> None:
        """Propagate query errors while closing the connection context."""
        engine, connection, connection_context = sqlalchemy_mocks
        connection.execute.side_effect = RuntimeError("query failed")
        source = SqlSource(engine, "SELECT id FROM customers")

        with pytest.raises(RuntimeError, match="query failed"):
            source.read()

        assert connection_context.__exit__.call_args.args[0] is RuntimeError

    def test_read_closes_result_when_result_processing_fails(
        self,
        sqlalchemy_mocks,
    ) -> None:
        """Close the result even if fetching its rows fails."""
        engine, connection, connection_context = sqlalchemy_mocks
        result = self.make_result(["id"], [])
        result.mappings.side_effect = RuntimeError("fetch failed")
        connection.execute.return_value = result

        source = SqlSource(engine, "SELECT id FROM customers")

        with pytest.raises(RuntimeError, match="fetch failed"):
            source.read()

        result.close.assert_called_once_with()
        assert connection_context.__exit__.call_args.args[0] is RuntimeError

    def test_connection_failure_propagates_without_disposing_borrowed_engine(
        self,
        sqlalchemy_mocks,
    ) -> None:
        engine, connection, connection_context = sqlalchemy_mocks
        failure = OperationalError(None, None, OSError("connection refused"))
        engine.connect.side_effect = failure

        with pytest.raises(OperationalError) as caught:
            SqlSource(engine, "SELECT id FROM records").read()

        assert caught.value is failure
        connection.execute.assert_not_called()
        connection_context.__exit__.assert_not_called()
        engine.dispose.assert_not_called()

    def test_arrow_conversion_failure_closes_sql_resources(
        self,
        sqlalchemy_mocks,
    ) -> None:
        engine, connection, connection_context = sqlalchemy_mocks
        result = self.make_result(["id"], [{"id": object()}])
        connection.execute.return_value = result
        failure = pa.ArrowInvalid("unrepresentable SQL value")

        def fail_conversion(_rows):
            raise failure

        with patch.object(SqlSource, "_rows_to_batch", side_effect=fail_conversion):
            with pytest.raises(pa.ArrowInvalid) as caught:
                SqlSource(engine, "SELECT id FROM records").read()

        assert caught.value is failure
        result.close.assert_called_once_with()
        connection_context.__exit__.assert_called_once()
        engine.dispose.assert_not_called()


class TestSqlSourceBatch:
    @pytest.fixture
    def sqlalchemy_mocks(self):
        """Provide mocked SQLAlchemy objects for streaming tests."""
        engine = MagicMock(spec=Engine)
        connection = MagicMock(spec=Connection)

        # SQLAlchemy modifies the connection in place and returns itself.
        connection.execution_options.return_value = connection

        connection_context = MagicMock()
        connection_context.__enter__.return_value = connection
        connection_context.__exit__.return_value = False

        engine.connect.return_value = connection_context

        return engine, connection, connection_context

    @pytest.fixture
    def streaming_result_factory(self):
        """Create a mocked SQLAlchemy result supporting incremental partitions."""

        def factory(
            columns: Sequence[str],
            partitions: Sequence[Sequence[Mapping[str, Any]]],
        ) -> tuple[MagicMock, MagicMock, list[int]]:
            result = MagicMock()
            result.keys.return_value = list(columns)

            # Model SQLAlchemy's MappingResult returned by result.mappings().
            mapping_result = MagicMock()
            result.mappings.return_value = mapping_result

            consumed_partitions: list[int] = []

            def iter_partitions():
                """Yield partitions while recording when each is consumed."""
                for index, partition in enumerate(partitions):
                    consumed_partitions.append(index)
                    yield partition

            # The iterator is lazy: creating it does not consume partitions.
            mapping_result.partitions.return_value = iter_partitions()

            return result, mapping_result, consumed_partitions

        return factory

    def test_returns_batches_of_specified_size(
        self,
        sqlalchemy_mocks,
        streaming_result_factory,
    ) -> None:
        """Ensure SqlSource yields batches incrementally using the configured batch size."""
        engine, connection, connection_context = sqlalchemy_mocks

        query = "SELECT id, name FROM customers"
        parameters = {"minimum_id": 1}
        batch_size = 2

        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
            {"id": 4, "name": "David"},
        ]

        expected_partitions = [
            rows[:batch_size],
            rows[batch_size:],
        ]

        result, mapping_result, consumed_partitions = streaming_result_factory(
            ["id", "name"],
            expected_partitions,
        )

        connection.execute.return_value = result

        source = SqlSource(
            engine,
            query,
            parameters=parameters,
            batch_size=batch_size,
        )

        batches = source.read()

        # Calling read() must not begin consuming the generator.
        engine.connect.assert_not_called()
        assert consumed_partitions == []

        # Retrieve the first batch.
        first_batch = next(batches)

        assert first_batch.table.equals(pa.Table.from_pylist(expected_partitions[0]))
        assert consumed_partitions == [0]

        # The second partition must not have been consumed yet.
        assert consumed_partitions != [0, 1]

        # Retrieve the second batch.
        second_batch = next(batches)

        assert second_batch.table.equals(pa.Table.from_pylist(expected_partitions[1]))
        assert consumed_partitions == [0, 1]

        # No additional batches should be produced.
        with pytest.raises(StopIteration):
            next(batches)

        # Verify SQLAlchemy configuration.
        connection.execution_options.assert_called_once_with(yield_per=batch_size)
        connection.execute.assert_called_once()
        executed_statement, executed_parameters = connection.execute.call_args.args

        assert str(executed_statement) == query
        assert executed_parameters == parameters
        result.mappings.assert_called_once_with()
        mapping_result.partitions.assert_called_once_with(batch_size)

        # Verify resource cleanup after complete consumption.
        result.close.assert_called_once_with()
        connection_context.__exit__.assert_called_once()

    def test_returns_partial_final_batch(
        self,
        sqlalchemy_mocks,
        streaming_result_factory,
    ) -> None:
        """Ensure the final batch contains the remaining rows."""
        engine, connection, connection_context = sqlalchemy_mocks

        batch_size = 2

        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
            {"id": 4, "name": "David"},
            {"id": 5, "name": "Eve"},
        ]

        expected_partitions = [
            rows[:2],
            rows[2:4],
            rows[4:],
        ]

        result, mapping_result, _ = streaming_result_factory(
            ["id", "name"],
            expected_partitions,
        )

        connection.execute.return_value = result

        source = SqlSource(
            engine,
            "SELECT id, name FROM customers",
            batch_size=batch_size,
        )

        batches = list(source.read())

        assert len(batches) == 3
        assert [batch.table.num_rows for batch in batches] == [2, 2, 1]

        for batch, expected_rows in zip(
            batches,
            expected_partitions,
            strict=True,
        ):
            assert batch.table.equals(pa.Table.from_pylist(expected_rows))

        mapping_result.partitions.assert_called_once_with(batch_size)
        result.close.assert_called_once_with()

        assert [
            row
            for batch in batches
            for row in batch.table.to_pylist()
        ] == rows

        result.close.assert_called_once_with()
        connection_context.__exit__.assert_called_once()
        engine.dispose.assert_not_called()

    def test_returns_no_batches_for_empty_result(
        self,
        sqlalchemy_mocks,
        streaming_result_factory,
    ) -> None:
        """Ensure an empty query result produces no batches."""
        engine, connection, _ = sqlalchemy_mocks

        batch_size = 2

        result, mapping_result, consumed_partitions = streaming_result_factory(
            ["id", "name"],
            [],
        )

        connection.execute.return_value = result

        source = SqlSource(
            engine,
            "SELECT id, name FROM customers",
            batch_size=batch_size,
        )

        batches = list(source.read())

        assert batches == []
        assert consumed_partitions == []

        mapping_result.partitions.assert_called_once_with(batch_size)
        result.close.assert_called_once_with()

    def test_closing_iterator_closes_sql_resources(
        self,
        sqlalchemy_mocks,
        streaming_result_factory,
    ) -> None:
        """Ensure closing a partially consumed iterator releases SQL resources."""
        engine, connection, connection_context = sqlalchemy_mocks

        batch_size = 2

        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
            {"id": 4, "name": "David"},
        ]

        result, _, consumed_partitions = streaming_result_factory(
            ["id", "name"],
            [rows[:2], rows[2:]],
        )

        connection.execute.return_value = result

        source = SqlSource(
            engine,
            "SELECT id, name FROM customers",
            batch_size=batch_size,
        )

        batches = source.read()

        assert isinstance(batches, Generator)

        first_batch = next(batches)

        assert first_batch.table.num_rows == batch_size
        assert consumed_partitions == [0]

        # Simulate a consumer abandoning the remaining batches.
        batches.close()

        result.close.assert_called_once_with()
        connection_context.__exit__.assert_called_once()
        engine.dispose.assert_not_called()

    @pytest.mark.parametrize("batch_size", [0, -10, -100, "invalid", 3.14, True, False])
    def test_rejects_invalid_batch_size_parameter(
        self,
        batch_size: int,
    ) -> None:
        engine = MagicMock()
        query = "SELECT id, name FROM customers"
        parameters = {"minimum_id": 1}

        with pytest.raises(ValueError, match="Batch size must be a positive integer"):
            SqlSource(engine, query, parameters=parameters, batch_size=batch_size)

    def test_result_with_smaller_configured_batch_size(
        self,
        sqlalchemy_mocks,
        streaming_result_factory,
    ):
        """Ensure a smaller result produces one batch and releases SQL resources."""
        engine, connection, connection_context = sqlalchemy_mocks

        batch_size = 10
        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
            {"id": 4, "name": "David"},
        ]

        result, mapping_result, consumed_partitions = streaming_result_factory(
            ["id", "name"],
            [rows],
        )

        connection.execute.return_value = result

        source = SqlSource(
            engine,
            "SELECT id, name FROM customers",
            batch_size=batch_size,
        )

        batches = list(source.read())

        assert len(batches) == 1
        assert batches[0].table.to_pylist() == rows
        assert consumed_partitions == [0]

        mapping_result.partitions.assert_called_once_with(batch_size)
        result.close.assert_called_once_with()
        connection_context.__exit__.assert_called_once()

    def test_result_with_exact_configured_batch_size(
        self,
        sqlalchemy_mocks,
        streaming_result_factory,
    ):
        """Ensure an exact-size result produces one batch and releases SQL resources."""
        engine, connection, connection_context = sqlalchemy_mocks

        batch_size = 4
        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
            {"id": 4, "name": "David"},
        ]

        result, mapping_result, consumed_partitions = streaming_result_factory(
            ["id", "name"],
            [rows],
        )

        connection.execute.return_value = result

        source = SqlSource(
            engine,
            "SELECT id, name FROM customers",
            batch_size=batch_size,
        )

        batches = list(source.read())

        assert len(batches) == 1
        assert batches[0].table.to_pylist() == rows
        assert consumed_partitions == [0]

        mapping_result.partitions.assert_called_once_with(batch_size)
        result.close.assert_called_once_with()
        connection_context.__exit__.assert_called_once()

    def test_result_with_partial_final_batch(
        self,
        sqlalchemy_mocks,
        streaming_result_factory,
    ):
        engine, connection, _ = sqlalchemy_mocks

        batch_size = 3

        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
            {"id": 4, "name": "David"},
        ]

        result, _, consumed_partitions = streaming_result_factory(
            ["id", "name"],
            [rows[:3], rows[3:]],
        )

        connection.execute.return_value = result

        source = SqlSource(
            engine,
            "SELECT id, name FROM customers",
            batch_size=batch_size,
        )

        batches = source.read()

        first_batch = next(batches)
        second_batch = next(batches)

        assert first_batch.table.num_rows == 3
        assert second_batch.table.num_rows == 1
    
    def test_streaming_query_execution_failure_closes_connection(
        self,
        sqlalchemy_mocks,
    ) -> None:
        """Ensure a query execution failure releases the connection."""
        engine, connection, connection_context = sqlalchemy_mocks

        failure = RuntimeError("query execution failed")
        connection.execute.side_effect = failure

        source = SqlSource(
            engine,
            "SELECT id FROM customers",
            batch_size=2,
        )

        batches = source.read()

        with pytest.raises(RuntimeError) as caught:
            next(batches)

        assert caught.value is failure
        connection.execution_options.assert_called_once_with(yield_per=2)
        connection.execute.assert_called_once()
        connection_context.__exit__.assert_called_once()
        assert connection_context.__exit__.call_args.args[0] is RuntimeError
        engine.dispose.assert_not_called()
    
    def test_partition_failure_after_first_batch_closes_sql_resources(
        self,
        sqlalchemy_mocks,
        streaming_result_factory,
    ) -> None:
        """Ensure a partition iteration failure releases SQL resources."""
        engine, connection, connection_context = sqlalchemy_mocks

        batch_size = 2
        failure = RuntimeError("partition iteration failed")

        result, mapping_result, _ = streaming_result_factory(
            ["id"],
            [],
        )

        def failing_partitions():
            yield [{"id": 1}, {"id": 2}]
            raise failure

        mapping_result.partitions.return_value = failing_partitions()
        connection.execute.return_value = result

        source = SqlSource(
            engine,
            "SELECT id FROM customers",
            batch_size=batch_size,
        )

        batches = source.read()

        first_batch = next(batches)

        assert first_batch.table.to_pylist() == [
            {"id": 1},
            {"id": 2},
        ]

        # Resources must remain open while the generator is suspended.
        result.close.assert_not_called()
        connection_context.__exit__.assert_not_called()

        with pytest.raises(RuntimeError) as caught:
            next(batches)

        assert caught.value is failure
        result.close.assert_called_once_with()
        connection_context.__exit__.assert_called_once()
        assert connection_context.__exit__.call_args.args[0] is RuntimeError
        engine.dispose.assert_not_called()
    
    def test_streaming_arrow_conversion_failure_closes_sql_resources(
        self,
        sqlalchemy_mocks,
        streaming_result_factory,
    ) -> None:
        """Ensure an Arrow conversion failure releases streaming SQL resources."""
        engine, connection, connection_context = sqlalchemy_mocks

        batch_size = 2
        failure = pa.ArrowInvalid("unrepresentable SQL value")

        result, _, _ = streaming_result_factory(
            ["id"],
            [
                [{"id": 1}],
                [{"id": 2}],
            ],
        )

        connection.execute.return_value = result

        source = SqlSource(
            engine,
            "SELECT id FROM customers",
            batch_size=batch_size,
        )

        original_conversion = source._rows_to_batch
        conversion_count = 0

        def convert_rows(rows):
            nonlocal conversion_count
            conversion_count += 1

            if conversion_count == 2:
                raise failure

            return original_conversion(rows)

        with patch.object(source, "_rows_to_batch", side_effect=convert_rows):
            batches = source.read()

            first_batch = next(batches)

            assert first_batch.table.to_pylist() == [{"id": 1}]

            result.close.assert_not_called()
            connection_context.__exit__.assert_not_called()

            with pytest.raises(pa.ArrowInvalid) as caught:
                next(batches)

        assert caught.value is failure
        assert conversion_count == 2
        result.close.assert_called_once_with()
        connection_context.__exit__.assert_called_once()
        assert connection_context.__exit__.call_args.args[0] is pa.ArrowInvalid
        engine.dispose.assert_not_called()
    
    def test_streaming_rejects_duplicate_result_column_names(
        self,
        sqlalchemy_mocks,
        streaming_result_factory,
    ) -> None:
        """Ensure streaming SQL results reject duplicate column names."""
        engine, connection, connection_context = sqlalchemy_mocks

        result, mapping_result, _ = streaming_result_factory(
            ["id", "id"],
            [],
        )

        connection.execute.return_value = result

        source = SqlSource(
            engine,
            "SELECT id, id FROM customers",
            batch_size=2,
        )

        batches = source.read()

        with pytest.raises(ValueError, match="duplicate column names"):
            next(batches)

        result.mappings.assert_not_called()
        mapping_result.partitions.assert_not_called()
        result.close.assert_called_once_with()
        connection_context.__exit__.assert_called_once()
        assert connection_context.__exit__.call_args.args[0] is ValueError
        engine.dispose.assert_not_called()
    

