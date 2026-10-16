"""Unit tests for the SQL sink."""

from unittest.mock import MagicMock, call, patch

import pyarrow as pa
import pytest

from etlrelay.core import Batch
from etlrelay.sinks.sql import SqlSink


class TestSqlSink:
    @pytest.fixture
    def sqlalchemy_mocks(self):
        """Provide a mocked engine, transaction, connection, and table."""
        engine = MagicMock()
        transaction_context = MagicMock()
        transaction_context.__exit__.return_value = False

        connection = MagicMock()
        transaction_context.__enter__.return_value = connection
        engine.begin.return_value = transaction_context

        target_table = MagicMock()
        target_table.c.keys.return_value = ["id", "name", "score"]
        insert_statement = object()
        target_table.insert.return_value = insert_statement

        return (
            engine,
            transaction_context,
            connection,
            target_table,
            insert_statement,
        )

    def make_batch(self, rows: list[dict[str, object]]) -> Batch:
        """Create a batch from row dictionaries."""
        return Batch(table=pa.Table.from_pylist(rows))

    def test_write_inserts_rows_using_reflected_table(
        self,
        sqlalchemy_mocks,
    ) -> None:
        """Reflect the table and execute a Core insert with batch rows."""
        (
            engine,
            transaction_context,
            connection,
            target_table,
            insert_statement,
        ) = sqlalchemy_mocks
        rows = [
            {"id": 2, "name": "Alice", "score": 9.5},
            {"id": 3, "name": "Bob", "score": None},
        ]
        sink = SqlSink(engine, "customers", schema="warehouse")

        with (
            patch("etlrelay.sinks.sql.MetaData") as metadata_factory,
            patch(
                "etlrelay.sinks.sql.Table",
                return_value=target_table,
            ) as table_factory,
        ):
            sink.write([self.make_batch(rows)])

        table_factory.assert_called_once_with(
            "customers",
            metadata_factory.return_value,
            schema="warehouse",
            autoload_with=connection,
        )
        connection.execute.assert_called_once_with(insert_statement, rows)
        engine.begin.assert_called_once_with()
        transaction_context.__exit__.assert_called_once_with(None, None, None)

    def test_write_skips_zero_row_batches(self, sqlalchemy_mocks) -> None:
        """Skip an empty batch without reflecting a table or opening a transaction."""
        engine, _, _, _, _ = sqlalchemy_mocks
        sink = SqlSink(engine, "customers")
        batch = Batch(
            table=pa.table(
                {
                    "id": pa.array([], type=pa.int64()),
                    "name": pa.array([], type=pa.string()),
                    "score": pa.array([], type=pa.float64()),
                }
            )
        )

        with patch("etlrelay.sinks.sql.Table") as table_factory:
            sink.write([batch])

        engine.begin.assert_not_called()
        table_factory.assert_not_called()

    def test_write_rejects_duplicate_batch_columns(self, sqlalchemy_mocks) -> None:
        """Reject duplicate input column names before opening a transaction."""
        engine, _, _, _, _ = sqlalchemy_mocks
        sink = SqlSink(engine, "customers")
        table = pa.Table.from_arrays(
            [
                pa.array([2], type=pa.int64()),
                pa.array([3], type=pa.int64()),
            ],
            names=["id", "id"],
        )

        with pytest.raises(ValueError, match="duplicate column names"):
            sink.write([Batch(table=table)])

        engine.begin.assert_not_called()

    def test_write_rejects_unknown_batch_columns(self, sqlalchemy_mocks) -> None:
        """Reject batch columns absent from the reflected target table."""
        (
            engine,
            transaction_context,
            connection,
            target_table,
            _,
        ) = sqlalchemy_mocks
        sink = SqlSink(engine, "customers")

        with patch(
            "etlrelay.sinks.sql.Table",
            return_value=target_table,
        ):
            with pytest.raises(ValueError, match="columns not present"):
                sink.write(
                    [
                        self.make_batch(
                            [
                                {
                                    "id": 2,
                                    "name": "Alice",
                                    "score": 9.5,
                                    "unexpected": "value",
                                }
                            ]
                        )
                    ]
                )

        connection.execute.assert_not_called()
        assert transaction_context.__exit__.call_args.args[0] is ValueError
        engine.begin.assert_called_once_with()

    def test_write_uses_one_transaction_per_batch_and_reflects_once(
        self,
        sqlalchemy_mocks,
    ) -> None:
        """Reflect the table once while opening a separate transaction per batch."""
        (
            engine,
            transaction_context,
            connection,
            target_table,
            insert_statement,
        ) = sqlalchemy_mocks
        first_rows = [{"id": 2, "name": "Alice", "score": 9.5}]
        second_rows = [{"id": 3, "name": "Bob", "score": 7.0}]
        sink = SqlSink(engine, "customers")

        with patch(
            "etlrelay.sinks.sql.Table",
            return_value=target_table,
        ) as table_factory:
            sink.write(
                [
                    self.make_batch(first_rows),
                    self.make_batch(second_rows),
                ]
            )

        table_factory.assert_called_once()
        assert engine.begin.call_count == 2
        assert transaction_context.__enter__.call_count == 2
        assert transaction_context.__exit__.call_count == 2
        assert connection.execute.call_args_list == [
            call(insert_statement, first_rows),
            call(insert_statement, second_rows),
        ]

    def test_write_propagates_insert_errors_and_exits_transaction(
        self,
        sqlalchemy_mocks,
    ) -> None:
        """Propagate database execution failures through the transaction context."""
        (
            engine,
            transaction_context,
            connection,
            target_table,
            _,
        ) = sqlalchemy_mocks
        connection.execute.side_effect = RuntimeError("insert failed")
        sink = SqlSink(engine, "customers")

        with patch(
            "etlrelay.sinks.sql.Table",
            return_value=target_table,
        ):
            with pytest.raises(RuntimeError, match="insert failed"):
                sink.write([self.make_batch([{"id": 2, "name": "Alice", "score": 9.5}])])

        assert transaction_context.__exit__.call_args.args[0] is RuntimeError
