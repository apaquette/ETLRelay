"""Integration tests for the SQL source."""

import logging
import os
from collections.abc import Generator, Iterator
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
import pytest
from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    event,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from etlrelay.sources import SqlSource

_RECORDS = [
    {"id": 1, "category": "include", "score": 9.5},
    {"id": 2, "category": "include", "score": None},
    {"id": 3, "category": "exclude", "score": 7.0},
]


def _create_source_records(engine: Engine) -> None:
    """Create and seed the common source table in an isolated test database/schema."""
    metadata = MetaData()
    records = Table(
        "records",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("category", String, nullable=False),
        Column("score", Float, nullable=True),
    )

    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(records.insert(), _RECORDS)


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Iterator[Engine]:
    """Create a temporary SQLite database with the common source records."""
    engine = create_engine(f"sqlite:///{tmp_path / 'sql_source.db'}")
    try:
        _create_source_records(engine)
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def postgresql_engine() -> Iterator[Engine]:
    """Create a PostgreSQL engine isolated to a unique schema for this test."""
    postgres_url = os.environ.get("ETLRELAY_TEST_POSTGRES_URL")
    if not postgres_url:
        pytest.skip("ETLRELAY_TEST_POSTGRES_URL is not set")

    admin_engine = create_engine(postgres_url)
    schema = f"etlrelay_test_{uuid4().hex}"
    schema_created = False
    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        schema_created = True

        engine = create_engine(
            postgres_url,
            connect_args={"options": f"-c search_path={schema}"},
        )
        try:
            _create_source_records(engine)
            yield engine
        finally:
            engine.dispose()
    finally:
        try:
            if schema_created:
                with admin_engine.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        finally:
            admin_engine.dispose()


@pytest.fixture(params=("sqlite_engine", "postgresql_engine"), ids=("sqlite", "postgresql"))
def sql_engine(request: pytest.FixtureRequest) -> Engine:
    """Run shared SQL source tests against each configured database engine."""
    return request.getfixturevalue(request.param)


class TestSqlSource:
    def test_read_queries_real_sql_records(self, sql_engine: Engine) -> None:
        """Execute a parameterized query and convert results to an Arrow batch."""
        source = SqlSource(
            sql_engine,
            """
            SELECT id, category, score
            FROM records
            WHERE category = :category
            ORDER BY id
            """,
            parameters={"category": "include"},
        )

        batches = list(source.read())

        assert len(batches) == 1
        assert batches[0].table.to_pylist() == [
            {"id": 1, "category": "include", "score": 9.5},
            {"id": 2, "category": "include", "score": None},
        ]

    def test_read_returns_no_batches_for_empty_query_result(
        self,
        sql_engine: Engine,
    ) -> None:
        """Return no batches when the query finds no rows."""
        source = SqlSource(
            sql_engine,
            "SELECT id, category, score FROM records WHERE category = :category",
            parameters={"category": "missing"},
        )

        assert list(source.read()) == []

    def test_read_binds_parameter_values_instead_of_interpolating_sql(
        self,
        sql_engine: Engine,
    ) -> None:
        """Treat SQL-looking input as a bound value, not executable SQL."""
        source = SqlSource(
            sql_engine,
            "SELECT id, category, score FROM records WHERE category = :category",
            parameters={"category": "include' OR 1=1 --"},
        )

        assert list(source.read()) == []

    def test_read_rejects_duplicate_result_column_names(
        self,
        sql_engine: Engine,
    ) -> None:
        """Reject duplicate column names produced by a real SQL query."""
        source = SqlSource(
            sql_engine,
            """
            SELECT id AS duplicate, category AS duplicate
            FROM records
            """,
        )

        with pytest.raises(ValueError, match="duplicate column names"):
            source.read()

    def test_read_logs_row_count_without_query_parameters(
        self,
        sql_engine: Engine,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Log the number of returned rows without logging SQL values."""
        secret = "private-database-credential"

        source = SqlSource(
            sql_engine,
            "SELECT :secret AS value",
            parameters={"secret": secret},
        )

        with caplog.at_level(logging.DEBUG, logger="etlrelay.sources.sql"):
            batches = list(source.read())

        messages = [
            record.message for record in caplog.records if record.name == "etlrelay.sources.sql"
        ]

        assert messages == ["SQL source created batch (1 rows)."]
        assert batches[0].table.to_pylist() == [{"value": secret}]
        assert secret not in caplog.text
        assert "SELECT :secret" not in caplog.text

    def test_read_failure_does_not_log_query_or_parameters(
        self,
        sql_engine: Engine,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Propagate SQL errors without logging statements or bound values."""
        secret = "private-query-parameter"

        source = SqlSource(
            sql_engine,
            "SELECT :secret FROM missing_table",
            parameters={"secret": secret},
        )

        with caplog.at_level(logging.DEBUG, logger="etlrelay.sources.sql"):
            with pytest.raises(SQLAlchemyError):
                source.read()

        messages = [
            record.message for record in caplog.records if record.name == "etlrelay.sources.sql"
        ]

        assert messages == []
        assert secret not in caplog.text
        assert "missing_table" not in caplog.text

    def test_batches_reject_populated_values_after_initial_null_only_partition(
        self,
        sql_engine: Engine,
    ) -> None:
        """Reject a later populated value when the first batch inferred null type."""
        metadata = MetaData()

        records = Table(
            "nullable_records",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("optional_value", Integer, nullable=True),
        )

        metadata.create_all(sql_engine)

        with sql_engine.begin() as connection:
            connection.execute(
                records.insert(),
                [
                    {"id": 1, "optional_value": None},
                    {"id": 2, "optional_value": 42},
                ],
            )

        source = SqlSource(
            sql_engine,
            """
            SELECT id, optional_value
            FROM nullable_records
            ORDER BY id
            """,
            batch_size=1,
        )

        batches = source.read()

        first_batch = next(batches)

        # The first partition establishes the inferred schema.
        assert first_batch.table.schema.field("optional_value").type == pa.null()

        # A later populated value cannot silently promote the established type.
        with pytest.raises(ValueError):
            next(batches)

    def test_batches_preserve_inferred_type_for_later_null_only_partition(
        self,
        sql_engine: Engine,
    ) -> None:
        """Preserve the inferred concrete type when a later partition contains nulls."""
        metadata = MetaData()

        records = Table(
            "nullable_records",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("optional_value", Integer, nullable=True),
        )

        metadata.create_all(sql_engine)

        with sql_engine.begin() as connection:
            connection.execute(
                records.insert(),
                [
                    {"id": 1, "optional_value": 42},
                    {"id": 2, "optional_value": None},
                ],
            )

        source = SqlSource(
            sql_engine,
            """
            SELECT id, optional_value
            FROM nullable_records
            ORDER BY id
            """,
            batch_size=1,
        )

        batches = list(source.read())

        expected_schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("optional_value", pa.int64()),
            ]
        )

        assert len(batches) == 2

        for batch in batches:
            assert batch.table.schema.equals(
                expected_schema,
                check_metadata=False,
            )

        assert [batch.table.to_pylist() for batch in batches] == [
            [{"id": 1, "optional_value": 42}],
            [{"id": 2, "optional_value": None}],
        ]

    def test_batches_preserve_null_type_when_column_contains_only_null_values(
        self,
        sql_engine: Engine,
    ) -> None:
        """Preserve an inferred null type across entirely-null partitions."""
        metadata = MetaData()

        records = Table(
            "nullable_records",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("optional_value", Integer, nullable=True),
        )

        metadata.create_all(sql_engine)

        with sql_engine.begin() as connection:
            connection.execute(
                records.insert(),
                [
                    {"id": 1, "optional_value": None},
                    {"id": 2, "optional_value": None},
                    {"id": 3, "optional_value": None},
                ],
            )

        source = SqlSource(
            sql_engine,
            """
            SELECT id, optional_value
            FROM nullable_records
            ORDER BY id
            """,
            batch_size=1,
        )

        batches = list(source.read())

        assert len(batches) == 3

        for batch in batches:
            assert batch.table.schema.field("optional_value").type == pa.null()

        assert all(
            batches[0].table.schema.equals(
                batch.table.schema,
                check_metadata=False,
            )
            for batch in batches[1:]
        )

    def test_batches_preserve_schema_across_multiple_sql_data_types(
        self,
        sql_engine: Engine,
    ) -> None:
        """Preserve all inferred field types across multiple batches."""
        source = SqlSource(
            sql_engine,
            """
            SELECT id, category, score
            FROM records
            ORDER BY id
            """,
            batch_size=1,
        )

        batches = list(source.read())

        expected_schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("category", pa.string()),
                pa.field("score", pa.float64()),
            ]
        )

        assert len(batches) == 3

        for batch in batches:
            assert batch.table.schema.equals(
                expected_schema,
                check_metadata=False,
            )

    @pytest.mark.parametrize(
        "expected_schema",
        [
            pa.schema(
                [
                    pa.field("record_id", pa.int64()),
                    pa.field("category", pa.string()),
                ]
            ),
            pa.schema(
                [
                    pa.field("category", pa.string()),
                    pa.field("id", pa.int64()),
                ]
            ),
        ],
        ids=["mismatched-field-names", "mismatched-field-order"],
    )
    def test_validate_batch_schema_rejects_incompatible_field_names_or_order(
        self,
        sql_engine: Engine,
        expected_schema: pa.Schema,
    ) -> None:
        """Reject schemas with different field names or ordering."""
        source = SqlSource(
            sql_engine,
            """
            SELECT id, category
            FROM records
            ORDER BY id
            """,
        )

        batch = next(source.read())

        with pytest.raises(ValueError):
            SqlSource._validate_batch_schema(batch.table, expected_schema)

    def test_validate_batch_schema_accepts_nulls_in_nullable_field(
        self,
        sql_engine: Engine,
    ) -> None:
        """Accept null values when the expected field is nullable."""
        source = SqlSource(
            sql_engine,
            """
            SELECT id, score
            FROM records
            WHERE category = :category
            ORDER BY id
            """,
            parameters={"category": "include"},
        )

        batch = next(source.read())

        expected_schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("score", pa.float64(), nullable=True),
            ]
        )

        assert batch.table.column("score").null_count == 1

        SqlSource._validate_batch_schema(batch.table, expected_schema)

    def test_validate_batch_schema_rejects_incompatible_field_types(
        self,
        sql_engine: Engine,
    ) -> None:
        """Reject populated values that have an incompatible Arrow type."""
        source = SqlSource(
            sql_engine,
            "SELECT 'not-an-integer' AS value",
        )

        batch = next(source.read())

        expected_schema = pa.schema(
            [
                pa.field("value", pa.int64()),
            ]
        )

        with pytest.raises(ValueError, match="Incompatible type"):
            SqlSource._validate_batch_schema(batch.table, expected_schema)

    def test_validate_batch_schema_rejects_nulls_in_non_nullable_field(
        self,
        sql_engine: Engine,
    ) -> None:
        """Reject null values when the expected field is non-nullable."""
        source = SqlSource(
            sql_engine,
            "SELECT NULL AS value",
        )

        batch = next(source.read())

        expected_schema = pa.schema(
            [
                pa.field("value", pa.int64(), nullable=False),
            ]
        )

        with pytest.raises(ValueError, match="non-nullable"):
            SqlSource._validate_batch_schema(batch.table, expected_schema)

    @pytest.mark.parametrize(
        "batch_size",
        [None, 1],
        ids=["unbatched", "batched"],
    )
    def test_explicit_schema_preserves_type_when_first_batch_contains_null(
        self,
        sql_engine: Engine,
        batch_size: int | None,
    ) -> None:
        """Use the supplied schema when the first partition contains null values."""
        metadata = MetaData()

        records = Table(
            "nullable_records",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("optional_value", Integer, nullable=True),
        )

        metadata.create_all(sql_engine)

        with sql_engine.begin() as connection:
            connection.execute(
                records.insert(),
                [
                    {"id": 1, "optional_value": None},
                    {"id": 2, "optional_value": 42},
                ],
            )

        expected_schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("optional_value", pa.int64()),
            ]
        )

        source = SqlSource(
            sql_engine,
            """
            SELECT id, optional_value
            FROM nullable_records
            ORDER BY id
            """,
            batch_size=batch_size,
            schema=expected_schema,
        )

        batches = list(source.read())

        assert len(batches) == (1 if batch_size is None else 2)

        for batch in batches:
            assert batch.table.schema.equals(
                expected_schema,
                check_metadata=False,
            )

        assert [batch.table.to_pylist() for batch in batches] == (
            [
                [
                    {"id": 1, "optional_value": None},
                    {"id": 2, "optional_value": 42},
                ]
            ]
            if batch_size is None
            else [
                [{"id": 1, "optional_value": None}],
                [{"id": 2, "optional_value": 42}],
            ]
        )

    @pytest.mark.parametrize(
        "batch_size",
        [None, 1],
        ids=["unbatched", "batched"],
    )
    def test_explicit_schema_preserves_type_for_entirely_null_column(
        self,
        sql_engine: Engine,
        batch_size: int | None,
    ) -> None:
        """Preserve a declared concrete type when every value is null."""
        metadata = MetaData()

        records = Table(
            "nullable_records",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("optional_value", Integer, nullable=True),
        )

        metadata.create_all(sql_engine)

        with sql_engine.begin() as connection:
            connection.execute(
                records.insert(),
                [
                    {"id": 1, "optional_value": None},
                    {"id": 2, "optional_value": None},
                ],
            )

        expected_schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("optional_value", pa.int64()),
            ]
        )

        source = SqlSource(
            sql_engine,
            """
            SELECT id, optional_value
            FROM nullable_records
            ORDER BY id
            """,
            batch_size=batch_size,
            schema=expected_schema,
        )

        batches = list(source.read())

        assert len(batches) == (1 if batch_size is None else 2)

        for batch in batches:
            assert batch.table.schema.equals(
                expected_schema,
                check_metadata=False,
            )

        assert sum(batch.table.column("optional_value").null_count for batch in batches) == 2

    @pytest.mark.parametrize(
        "batch_size",
        [None, 1],
        ids=["unbatched", "batched"],
    )
    def test_explicit_schema_rejects_incompatible_data_types(
        self,
        sql_engine: Engine,
        batch_size: int | None,
    ) -> None:
        """Reject SQL values that cannot be represented by the supplied schema."""
        expected_schema = pa.schema(
            [
                pa.field("value", pa.int64()),
            ]
        )

        source = SqlSource(
            sql_engine,
            "SELECT 'not-an-integer' AS value",
            batch_size=batch_size,
            schema=expected_schema,
        )

        with pytest.raises(ValueError):
            list(source.read())

    @pytest.mark.parametrize(
        "batch_size",
        [None, 1],
        ids=["unbatched", "batched"],
    )
    def test_explicit_schema_rejects_nulls_in_non_nullable_fields(
        self,
        sql_engine: Engine,
        batch_size: int | None,
    ) -> None:
        """Reject null values for fields declared non-nullable."""
        expected_schema = pa.schema(
            [
                pa.field("value", pa.int64(), nullable=False),
            ]
        )

        source = SqlSource(
            sql_engine,
            "SELECT NULL AS value",
            batch_size=batch_size,
            schema=expected_schema,
        )

        with pytest.raises(ValueError, match="non-nullable"):
            list(source.read())

    @pytest.mark.parametrize(
        "expected_schema",
        [
            pa.schema(
                [
                    pa.field("id", pa.int64()),
                    pa.field("unexpected", pa.string()),
                ]
            ),
            pa.schema(
                [
                    pa.field("category", pa.string()),
                    pa.field("id", pa.int64()),
                ]
            ),
        ],
        ids=["mismatched-field-name", "mismatched-field-order"],
    )
    def test_explicit_schema_rejects_mismatched_result_columns(
        self,
        sql_engine: Engine,
        expected_schema: pa.Schema,
    ) -> None:
        """Reject supplied schemas with mismatched result names or ordering."""
        source = SqlSource(
            sql_engine,
            "SELECT 1 AS id, 'example' AS category",
            schema=expected_schema,
        )

        with pytest.raises(ValueError):
            list(source.read())

    @pytest.mark.parametrize(
        "batch_size",
        [None, 1],
        ids=["unbatched", "batched"],
    )
    def test_explicit_schema_preserves_empty_result_behaviour(
        self,
        sql_engine: Engine,
        batch_size: int | None,
    ) -> None:
        """Return no batches when a query produces no rows and a schema is supplied."""
        expected_schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("category", pa.string()),
            ]
        )

        source = SqlSource(
            sql_engine,
            """
            SELECT 1 AS id, 'example' AS category
            WHERE 1 = 0
            """,
            batch_size=batch_size,
            schema=expected_schema,
        )

        assert list(source.read()) == []

    def test_sqlalchemy_partitions_results_in_row_order(self, sql_engine: Engine) -> None:
        """Ensure SQLAlchemy result partitions preserve row order and batch sizes."""
        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
            {"id": 4, "name": "David"},
            {"id": 5, "name": "Eve"},
        ]

        with sql_engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE customers (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO customers (id, name)
                    VALUES (:id, :name)
                    """
                ),
                rows,
            )

        source = SqlSource(
            sql_engine,
            "SELECT id, name FROM customers ORDER BY id",
            batch_size=2,
        )

        batches = list(source.read())

        assert [batch.table.num_rows for batch in batches] == [2, 2, 1]
        assert [row for batch in batches for row in batch.table.to_pylist()] == rows


class TestSqlite:
    def test_malformed_sql_returns_connection_to_pool_without_logging_query(
        self,
        sqlite_engine: Engine,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Use actual SQLite syntax failure and observe the connection check-in."""
        events: list[str] = []

        def checkout(*_args: object) -> None:
            events.append("checkout")

        def checkin(*_args: object) -> None:
            events.append("checkin")

        event.listen(sqlite_engine, "checkout", checkout)
        event.listen(sqlite_engine, "checkin", checkin)
        try:
            with caplog.at_level(logging.DEBUG, logger="etlrelay"):
                with pytest.raises(OperationalError):
                    SqlSource(sqlite_engine, "SELECT FROM SECRET_SQL_PAYLOAD").read()
            assert events == ["checkout", "checkin"]
            assert "SECRET_SQL_PAYLOAD" not in caplog.text
            assert list(SqlSource(sqlite_engine, "SELECT 1 AS id").read())[0].table.to_pylist() == [
                {"id": 1}
            ]
        finally:
            event.remove(sqlite_engine, "checkout", checkout)
            event.remove(sqlite_engine, "checkin", checkin)

    def test_batches_reject_incompatible_populated_values(
        self,
        sqlite_engine: Engine,
    ) -> None:
        """Reject populated values that conflict with the inferred schema."""
        with sqlite_engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE mixed_records (
                        id INTEGER PRIMARY KEY,
                        value
                    )
                    """
                )
            )

            connection.execute(
                text(
                    """
                    INSERT INTO mixed_records (id, value)
                    VALUES (1, 42), (2, 'not-an-integer')
                    """
                )
            )

        source = SqlSource(
            sqlite_engine,
            "SELECT id, value FROM mixed_records ORDER BY id",
            batch_size=1,
        )

        batches = source.read()

        first_batch = next(batches)

        assert first_batch.table.schema.field("value").type == pa.int64()

        with pytest.raises(ValueError):
            next(batches)

    def test_source_reinfers_schema_for_each_execution(
        self,
        sqlite_engine: Engine,
    ) -> None:
        """Infer a fresh schema when the same source executes another query."""
        with sqlite_engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE schema_records (
                        id INTEGER PRIMARY KEY,
                        value
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO schema_records (id, value)
                    VALUES (1, 42)
                    """
                )
            )

        source = SqlSource(
            sqlite_engine,
            """
            SELECT value
            FROM schema_records
            ORDER BY id
            """,
            batch_size=1,
        )

        # First execution: infer an integer column.
        first_batches = list(source.read())

        assert len(first_batches) == 1
        assert first_batches[0].table.schema.field("value").type == pa.int64()
        assert first_batches[0].table.to_pylist() == [{"value": 42}]

        # Change the underlying SQLite value to a string.
        with sqlite_engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE schema_records
                    SET value = 'forty-two'
                    WHERE id = 1
                    """
                )
            )

        # Second execution: independently infer a string column.
        second_batches = list(source.read())

        assert len(second_batches) == 1
        assert second_batches[0].table.schema.field("value").type == pa.string()
        assert second_batches[0].table.to_pylist() == [{"value": "forty-two"}]


class TestPostgresql:
    def test_read_maps_postgresql_data_types_to_arrow(self, postgresql_engine: Engine) -> None:
        """Verify PostgreSQL values are converted to the expected Arrow types."""
        source = SqlSource(
            postgresql_engine,
            """
            SELECT
                CAST(1 AS SMALLINT) AS smallint_value,
                CAST(2 AS INTEGER) AS integer_value,
                CAST(3 AS BIGINT) AS bigint_value,
                CAST(1.25 AS REAL) AS real_value,
                CAST(2.5 AS DOUBLE PRECISION) AS double_value,
                CAST(12345.67 AS NUMERIC(7, 2)) AS numeric_value,
                CAST(TRUE AS BOOLEAN) AS boolean_value,
                CAST('text value' AS TEXT) AS text_value,
                CAST('varchar value' AS VARCHAR(20)) AS varchar_value,
                CAST('2026-01-02' AS DATE) AS date_value,
                CAST('03:04:05' AS TIME) AS time_value,
                CAST('2026-01-02 03:04:05' AS TIMESTAMP) AS timestamp_value,
                CAST('2026-01-02 03:04:05+00:00' AS TIMESTAMPTZ)
                    AS timestamptz_value,
                CAST(NULL AS INTEGER) AS null_value
            """,
        )

        batches = list(source.read())

        assert len(batches) == 1

        batch = batches[0].table
        schema = batch.schema

        assert batch.to_pylist() == [
            {
                "smallint_value": 1,
                "integer_value": 2,
                "bigint_value": 3,
                "real_value": 1.25,
                "double_value": 2.5,
                "numeric_value": Decimal("12345.67"),
                "boolean_value": True,
                "text_value": "text value",
                "varchar_value": "varchar value",
                "date_value": date(2026, 1, 2),
                "time_value": time(3, 4, 5),
                "timestamp_value": datetime(2026, 1, 2, 3, 4, 5),
                "timestamptz_value": datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
                "null_value": None,
            }
        ]

        # PostgreSQL integer types are represented as Arrow int64.
        for column in ("smallint_value", "integer_value", "bigint_value"):
            assert schema.field(column).type == pa.int64()

        # PostgreSQL REAL and DOUBLE PRECISION are both represented as float64.
        for column in ("real_value", "double_value"):
            assert schema.field(column).type == pa.float64()

        numeric_type = schema.field("numeric_value").type
        assert pa.types.is_decimal(numeric_type)
        assert numeric_type.scale == 2
        assert numeric_type.precision >= 7

        assert schema.field("boolean_value").type == pa.bool_()
        assert schema.field("text_value").type == pa.string()
        assert schema.field("varchar_value").type == pa.string()
        assert pa.types.is_date32(schema.field("date_value").type)
        assert pa.types.is_time64(schema.field("time_value").type)

        timestamp_type = schema.field("timestamp_value").type
        assert pa.types.is_timestamp(timestamp_type)
        assert timestamp_type.tz is None

        timestamptz_type = schema.field("timestamptz_value").type
        assert pa.types.is_timestamp(timestamptz_type)
        assert timestamptz_type.tz is not None

        assert schema.field("null_value").type == pa.null()

    def test_read_supports_schema_qualified_reserved_and_mixed_case_identifiers(
        self,
        postgresql_engine: Engine,
    ) -> None:
        """Read from a schema-qualified table with quoted PostgreSQL identifiers."""
        with postgresql_engine.connect() as connection:
            schema_name = connection.scalar(text("SELECT current_schema()"))

        assert schema_name is not None

        # The schema name is generated by the fixture and contains only
        # lowercase letters, numbers, and underscores.
        with postgresql_engine.begin() as connection:
            connection.execute(
                text(
                    f"""
                    CREATE TABLE "{schema_name}"."Order" (
                        "RecordID" INTEGER PRIMARY KEY,
                        "DisplayName" TEXT NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    f"""
                    INSERT INTO "{schema_name}"."Order"
                        ("RecordID", "DisplayName")
                    VALUES
                        (:record_id, :display_name)
                    """
                ),
                {"record_id": 1, "display_name": "Example record"},
            )

        source = SqlSource(
            postgresql_engine,
            f"""
            SELECT "RecordID", "DisplayName"
            FROM "{schema_name}"."Order"
            ORDER BY "RecordID"
            """,
        )

        batches = list(source.read())

        assert len(batches) == 1
        assert batches[0].table.to_pylist() == [{"RecordID": 1, "DisplayName": "Example record"}]

    def test_streaming_returns_connection_to_pool_after_early_close(
        self,
        postgresql_engine: Engine,
    ) -> None:
        """Return the connection to the pool when a streaming iterator is closed."""
        events: list[str] = []

        def checkout(*_args: object) -> None:
            events.append("checkout")

        def checkin(*_args: object) -> None:
            events.append("checkin")

        event.listen(postgresql_engine, "checkout", checkout)
        event.listen(postgresql_engine, "checkin", checkin)

        iterator = SqlSource(
            postgresql_engine,
            "SELECT id FROM records ORDER BY id",
            batch_size=1,
        ).read()

        try:
            assert isinstance(iterator, Generator)

            first_batch = next(iterator)

            assert first_batch.table.to_pylist() == [{"id": 1}]

            iterator.close()

            assert events == ["checkout", "checkin"]
        finally:
            event.remove(postgresql_engine, "checkout", checkout)
            event.remove(postgresql_engine, "checkin", checkin)

    def test_streaming_returns_connection_to_pool_after_batch_processing_failure(
        self,
        postgresql_engine: Engine,
    ) -> None:
        """Return the connection to the pool when batch processing raises an error."""
        events: list[str] = []

        def checkout(*_args: object) -> None:
            events.append("checkout")

        def checkin(*_args: object) -> None:
            events.append("checkin")

        event.listen(postgresql_engine, "checkout", checkout)
        event.listen(postgresql_engine, "checkin", checkin)

        source = SqlSource(
            postgresql_engine,
            "SELECT CAST('not-an-integer' AS TEXT) AS value",
            batch_size=1,
            schema=pa.schema([pa.field("value", pa.int64())]),
        )

        try:
            iterator = source.read()

            with pytest.raises(ValueError):
                next(iterator)

            assert events == ["checkout", "checkin"]
        finally:
            event.remove(postgresql_engine, "checkout", checkout)
            event.remove(postgresql_engine, "checkin", checkin)
