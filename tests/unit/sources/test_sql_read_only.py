"""Unit tests for secure, read-only SQL source query validation."""

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from sqlalchemy import bindparam, column, create_engine, literal, select, table, text
from sqlalchemy.engine import Engine

from etlrelay.sources.sql import SqlSource


@pytest.fixture
def engine_for_dialect() -> Callable[[str], Engine]:
    """Return a lightweight SQLAlchemy engine double with a selected dialect."""

    def build(dialect: str) -> Engine:
        engine = MagicMock(spec=Engine)
        engine.dialect.name = dialect
        return engine

    return build


def _assert_query_rejected(
    engine: Engine,
    query: str,
    *,
    reason: str | None = None,
) -> None:
    """Assert query policy validation rejects a query before database I/O."""
    with pytest.raises(ValueError) as caught:
        SqlSource(engine, query)

    message = str(caught.value)
    assert message
    assert "source.query" in message or "dialect" in message.lower()
    if reason is not None:
        assert reason.lower() in message.lower()
    engine.connect.assert_not_called()


class TestSqlSourceReadOnlyQueryPolicy:
    """Verify the SQL text read-only policy independently of database execution."""

    @pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
    @pytest.mark.parametrize(
        "query",
        [
            "SELECT id, name FROM customers",
            "SELECT id FROM customers WHERE id = :customer_id",
            (
                "SELECT c.id, o.id "
                "FROM customers AS c "
                "JOIN orders AS o ON o.customer_id = c.id "
                "WHERE o.total > (SELECT AVG(total) FROM orders)"
            ),
            (
                "WITH customer_orders AS ("
                "SELECT customer_id, COUNT(*) AS order_count "
                "FROM orders GROUP BY customer_id"
                ") SELECT customer_id, order_count FROM customer_orders"
            ),
            (
                "WITH RECURSIVE sequence(n) AS ("
                "SELECT 1 UNION ALL SELECT n + 1 FROM sequence WHERE n < 3"
                ") SELECT n FROM sequence"
            ),
            (
                "SELECT id FROM customers "
                "UNION SELECT customer_id AS id FROM orders "
                "INTERSECT SELECT id FROM eligible_customers "
                "EXCEPT SELECT id FROM blocked_customers"
            ),
            (
                "SELECT customer_id, COUNT(*) AS order_count, "
                "ROW_NUMBER() OVER (ORDER BY customer_id) AS row_number "
                "FROM orders GROUP BY customer_id"
            ),
            'SELECT "c"."id" FROM "analytics"."customers" AS "c"',
        ],
        ids=[
            "basic-select",
            "bound-parameter",
            "join-and-subquery",
            "common-table-expression",
            "recursive-common-table-expression",
            "read-only-set-operations",
            "aggregate-and-window-function",
            "quoted-schema-qualified-identifiers",
        ],
    )
    def test_accepts_permitted_read_only_sql(
        self,
        engine_for_dialect: Callable[[str], Engine],
        dialect: str,
        query: str,
    ) -> None:
        """Accept the supported analytical SELECT structures for both dialects."""
        engine = engine_for_dialect(dialect)

        source = SqlSource(engine, query)

        assert isinstance(source, SqlSource)
        engine.connect.assert_not_called()

    @pytest.mark.parametrize(
        ("dialect", "query"),
        [
            ("sqlite", "INSERT INTO customers (id) VALUES (1)"),
            ("sqlite", "UPDATE customers SET active = 0 WHERE id = 1"),
            ("sqlite", "DELETE FROM customers WHERE id = 1"),
            ("postgresql", "MERGE INTO customers USING staging ON customers.id = staging.id "
             "WHEN MATCHED THEN UPDATE SET name = staging.name"),
            ("postgresql", "CREATE TABLE copied_customers (id INTEGER)"),
            ("postgresql", "ALTER TABLE customers ADD COLUMN active BOOLEAN"),
            ("postgresql", "DROP TABLE customers"),
            ("postgresql", "TRUNCATE TABLE customers"),
        ],
        ids=[
            "insert",
            "update",
            "delete",
            "merge",
            "create",
            "alter",
            "drop",
            "truncate",
        ],
    )
    def test_rejects_dml_and_ddl_statements(
        self,
        engine_for_dialect: Callable[[str], Engine],
        dialect: str,
        query: str,
    ) -> None:
        """Reject data-modifying and schema-modifying root statements."""
        _assert_query_rejected(engine_for_dialect(dialect), query)

    @pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
    def test_rejects_multiple_statements(
        self,
        engine_for_dialect: Callable[[str], Engine],
        dialect: str,
    ) -> None:
        """Reject a second statement even when the first statement is a SELECT."""
        _assert_query_rejected(
            engine_for_dialect(dialect),
            "SELECT id FROM customers; DELETE FROM customers",
        )

    def test_rejects_data_modifying_cte_inside_select(
        self,
        engine_for_dialect: Callable[[str], Engine],
    ) -> None:
        """Inspect CTE contents rather than accepting a SELECT root unconditionally."""
        query = (
            "WITH deleted AS ("
            "DELETE FROM customers WHERE id = 1 RETURNING id"
            ") SELECT id FROM deleted"
        )

        _assert_query_rejected(engine_for_dialect("postgresql"), query)

    def test_rejects_select_into(
        self,
        engine_for_dialect: Callable[[str], Engine],
    ) -> None:
        """Reject SELECT INTO because it creates or populates a table."""
        _assert_query_rejected(
            engine_for_dialect("postgresql"),
            "SELECT id, name INTO archived_customers FROM customers",
        )

    def test_rejects_row_locking_clause(
        self,
        engine_for_dialect: Callable[[str], Engine],
    ) -> None:
        """Reject SELECT statements requesting database row locks."""
        _assert_query_rejected(
            engine_for_dialect("postgresql"),
            "SELECT id FROM customers FOR UPDATE",
        )

    @pytest.mark.parametrize(
        ("dialect", "query"),
        [
            ("postgresql", "BEGIN"),
            ("postgresql", "COMMIT"),
            ("postgresql", "ROLLBACK"),
            ("postgresql", "SAVEPOINT checkpoint"),
            ("postgresql", "RELEASE SAVEPOINT checkpoint"),
            ("postgresql", "SET ROLE reporting"),
            ("postgresql", "SET search_path TO analytics"),
            ("sqlite", "PRAGMA query_only = OFF"),
        ],
        ids=[
            "begin",
            "commit",
            "rollback",
            "savepoint",
            "release-savepoint",
            "set-role",
            "set-search-path",
            "pragma",
        ],
    )
    def test_rejects_transaction_and_session_commands(
        self,
        engine_for_dialect: Callable[[str], Engine],
        dialect: str,
        query: str,
    ) -> None:
        """Reject transaction management and session/database configuration."""
        _assert_query_rejected(engine_for_dialect(dialect), query)

    def test_rejects_sql_that_cannot_be_parsed(
        self,
        engine_for_dialect: Callable[[str], Engine],
    ) -> None:
        """Fail closed when the selected dialect cannot parse the supplied SQL."""
        _assert_query_rejected(
            engine_for_dialect("sqlite"),
            "SELECT * FROM customers WHERE (",
        )

    def test_unsupported_dialect_fails_closed(
        self,
        engine_for_dialect: Callable[[str], Engine],
    ) -> None:
        """Do not execute a query when the engine dialect has no read-only policy."""
        engine = engine_for_dialect("mysql")

        with pytest.raises(ValueError) as caught:
            SqlSource(engine, "SELECT id FROM customers")

        assert "dialect" in str(caught.value).lower()
        engine.connect.assert_not_called()

    def test_validation_error_does_not_echo_query_text_or_sensitive_values(
        self,
        engine_for_dialect: Callable[[str], Engine],
    ) -> None:
        """Keep query contents out of parser and policy validation errors."""
        secret = "SQL_SOURCE_QUERY_SECRET_3c91a7"
        query = f"SELECT * FROM customers WHERE ({secret}"

        with pytest.raises(ValueError) as caught:
            SqlSource(engine_for_dialect("sqlite"), query)

        assert secret not in str(caught.value)


class TestSqlSourceSelectExpressions:
    """Verify that structured SQLAlchemy queries receive the same policy checks."""

    def test_accepts_parameterized_select_expression(
        self,
        engine_for_dialect: Callable[[str], Engine],
    ) -> None:
        """Accept SQLAlchemy Core Select expressions with separately bound values."""
        customers = table("customers", column("id"), column("name"))
        query = (
            select(customers.c.id, customers.c.name)
            .where(customers.c.id > bindparam("minimum_id"))
            .order_by(customers.c.id)
        )

        source = SqlSource(
            engine_for_dialect("sqlite"),
            query,
            parameters={"minimum_id": 10},
        )

        assert isinstance(source, SqlSource)

    def test_accepts_allowlisted_dynamic_table_selection(
        self,
        engine_for_dialect: Callable[[str], Engine],
    ) -> None:
        """Allow Core expressions built from application-approved table objects."""
        approved_tables = {
            "customers": table("customers", column("id")),
            "orders": table("orders", column("id")),
        }
        query = select(approved_tables["customers"].c.id)

        source = SqlSource(engine_for_dialect("sqlite"), query)

        assert isinstance(source, SqlSource)
        with pytest.raises(KeyError):
            approved_tables["unapproved_table"]

    @pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
    def test_rejects_select_expression_with_multiple_statement_text_fragment(
        self,
        engine_for_dialect: Callable[[str], Engine],
        dialect: str,
    ) -> None:
        """Do not treat Select expressions containing raw SQL fragments as safe."""
        query = select(literal(1)).where(text("1 = 1; DELETE FROM customers"))

        engine = engine_for_dialect(dialect)
        with pytest.raises(ValueError):
            SqlSource(engine, query)

        engine.connect.assert_not_called()

    def test_accepts_suspicious_looking_text_inside_a_string_literal(
        self,
        engine_for_dialect: Callable[[str], Engine],
    ) -> None:
        """Do not mistake SQL keywords inside a quoted literal for SQL operations."""
        query = "SELECT 'INSERT INTO customers; DROP TABLE customers' AS message"

        source = SqlSource(engine_for_dialect("sqlite"), query)

        assert isinstance(source, SqlSource)


class TestSqlSourceParameterBindingRegression:
    """Verify values remain data and cannot alter the validated query structure."""

    def test_sql_looking_parameter_value_does_not_broaden_query_results(
        self,
    ) -> None:
        """A SQL-looking value is bound as data rather than interpolated into SQL."""
        engine = create_engine("sqlite:///:memory:")

        try:
            with engine.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
                )
                connection.exec_driver_sql(
                    "INSERT INTO customers (id, name) VALUES (1, 'Ada'), (2, 'Grace')"
                )

            source = SqlSource(
                engine,
                "SELECT id, name FROM customers WHERE name = :name",
                parameters={"name": "' OR 1=1 --"},
            )

            assert list(source.read()) == []
        finally:
            engine.dispose()
