"""Unit tests for the SQL sink."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, call, patch

import pyarrow as pa
import pytest
from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.engine import Engine

from etlrelay.core import Batch
from etlrelay.sinks import SqlSink
from etlrelay.sources import SqlSource


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

    def test_write_skips_empty_batch_schema_before_valid_batch(
        self,
        sqlalchemy_mocks,
    ) -> None:
        """An empty batch does not trigger SQL reflection or column validation."""
        (
            engine,
            _,
            connection,
            target_table,
            insert_statement,
        ) = sqlalchemy_mocks

        empty_batch = Batch(
            table=pa.table(
                {
                    "unknown": pa.array([], type=pa.string()),
                }
            )
        )

        valid_rows = [
            {"id": 2, "name": "Alice", "score": 9.5},
        ]

        valid_batch = self.make_batch(valid_rows)

        sink = SqlSink(engine, "customers")

        with patch(
            "etlrelay.sinks.sql.Table",
            return_value=target_table,
        ) as table_factory:
            sink.write([empty_batch, valid_batch])

        engine.begin.assert_called_once_with()
        table_factory.assert_called_once()

        connection.execute.assert_called_once_with(
            insert_statement,
            valid_rows,
        )


def test_sql_sink_logs_commit_only_after_transaction_completes(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Report successful commits only after the transaction exits."""
    batch = Batch(table=pa.table({"id": [1]}))

    engine = Mock(spec=Engine)
    connection = Mock()

    target_table = Table(
        "records",
        MetaData(),
        Column("id", Integer),
    )

    messages_before_commit: list[str] = []

    @contextmanager
    def transaction() -> Iterator[Mock]:
        yield connection

        # Observe logging immediately before the transaction
        # context manager finishes its simulated commit.
        messages_before_commit.extend(caplog.messages)

    engine.begin.side_effect = transaction

    sink = SqlSink(engine, "records")
    monkeypatch.setattr(
        sink,
        "_reflect_table",
        lambda _: target_table,
    )

    with caplog.at_level(logging.DEBUG, logger="etlrelay.sinks.sql"):
        sink.write([batch])

    commit_message = "SQL sink committed batch (1 rows)."

    assert commit_message not in messages_before_commit
    assert commit_message in caplog.messages

    connection.execute.assert_called_once()
    engine.dispose.assert_not_called()


def test_sql_sink_does_not_log_success_when_commit_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Preserve commit failures without reporting a successful commit."""
    batch = Batch(table=pa.table({"id": [1]}))

    engine = Mock(spec=Engine)
    connection = Mock()

    target_table = Table(
        "records",
        MetaData(),
        Column("id", Integer),
    )

    commit_error = RuntimeError("secret-commit-failure")

    @contextmanager
    def failing_transaction() -> Iterator[Mock]:
        yield connection
        raise commit_error

    engine.begin.side_effect = failing_transaction

    sink = SqlSink(engine, "records")
    monkeypatch.setattr(
        sink,
        "_reflect_table",
        lambda _: target_table,
    )

    with caplog.at_level(logging.DEBUG, logger="etlrelay.sinks.sql"):
        with pytest.raises(RuntimeError) as exc_info:
            sink.write([batch])

    assert exc_info.value is commit_error

    assert "SQL sink committed batch" not in caplog.text
    assert "secret-commit-failure" not in caplog.text

    connection.execute.assert_called_once()
    engine.dispose.assert_not_called()


def test_sql_source_closes_result_and_connection_when_iteration_fails() -> None:
    """Close owned SQL resources while preserving the query failure."""
    engine = Mock(spec=Engine)

    connection_context = MagicMock()
    connection = Mock()

    connection_context.__enter__.return_value = connection
    engine.connect.return_value = connection_context

    result = Mock()
    result.keys.return_value = ["id"]

    failure = RuntimeError("query-fetch-failure")

    def failing_rows():
        yield {"id": 1}
        raise failure

    result.mappings.return_value = failing_rows()
    connection.execute.return_value = result

    source = SqlSource(engine, "SELECT id FROM records")

    with pytest.raises(RuntimeError) as exc_info:
        source.read()

    assert exc_info.value is failure

    result.close.assert_called_once_with()
    connection_context.__exit__.assert_called_once()

    # SqlSource borrows the engine; it must never dispose of it.
    engine.dispose.assert_not_called()


def test_sql_sink_skips_empty_batch_without_opening_transaction() -> None:
    """An empty batch must not open a transaction or dispose the engine."""
    engine = Mock(spec=Engine)

    sink = SqlSink(engine, "records")

    batch = Batch(
        table=pa.table(
            {
                "id": pa.array([], type=pa.int64()),
            }
        )
    )

    sink.write([batch])

    engine.begin.assert_not_called()
    engine.dispose.assert_not_called()
