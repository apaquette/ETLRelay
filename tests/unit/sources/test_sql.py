"""Unit tests for the SQL source."""

from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest
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

    def test_arrow_conversion_failure_occurs_after_sql_resources_are_closed(
        self,
        sqlalchemy_mocks,
    ) -> None:
        engine, connection, connection_context = sqlalchemy_mocks
        result = self.make_result(["id"], [{"id": object()}])
        connection.execute.return_value = result
        failure = pa.ArrowInvalid("unrepresentable SQL value")

        def fail_conversion(_rows):
            result.close.assert_called_once_with()
            connection_context.__exit__.assert_called_once_with(None, None, None)
            raise failure

        with patch.object(SqlSource, "_rows_to_batch", side_effect=fail_conversion):
            with pytest.raises(pa.ArrowInvalid) as caught:
                SqlSource(engine, "SELECT id FROM records").read()

        assert caught.value is failure
        engine.dispose.assert_not_called()
