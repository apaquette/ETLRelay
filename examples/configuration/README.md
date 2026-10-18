# YAML Configuration Examples

These nine YAML files exercise every supported schema-v1 source/sink combination using CSV, Parquet, and SQLite:

| File | Source | Sink |
|---|---|---|
| `csv_to_csv.yaml` | CSV file | CSV file |
| `csv_to_parquet.yaml` | CSV file | Parquet file |
| `parquet_to_csv.yaml` | Parquet file | CSV file |
| `parquet_to_parquet.yaml` | Parquet file | Parquet file |
| `csv_to_sql.yaml` | CSV file | SQL table |
| `parquet_to_sql.yaml` | Parquet file | SQL table |
| `sql_to_csv.yaml` | SQL query | CSV file |
| `sql_to_parquet.yaml` | SQL query | Parquet file |
| `sql_to_sql.yaml` | SQL query | SQL table |

Run from the repository root. The data-preparation script recreates the sample files and both SQLite databases (including the existing target table):

```bash
python examples/configuration/prepare_demo_data.py
```

Configure the environment variables before executing SQL examples:

```bash
export ETLRELAY_SOURCE_DATABASE_URL="sqlite:///examples/configuration/data/source.db"
export ETLRELAY_SINK_DATABASE_URL="sqlite:///examples/configuration/data/sink.db"
```

Run an example with the shared runner:

```bash
python examples/configuration/run.py examples/configuration/csv_to_csv.yaml
python examples/configuration/run.py examples/configuration/sql_to_sql.yaml
```

The file source and sink paths are interpreted from the process working directory through the configured local-storage base path. The SQL configurations refer to environment-variable names; they do not contain SQLAlchemy URLs. The demo values are local SQLite URLs without credentials.

The examples deliberately use the same fields (`id`, `amount`, `state`) and processors: select `id` and `amount`, filter for non-negative amounts, and rename `id` to `record_id`. SQL sink targets have the matching columns `record_id` and `amount` and are created by the setup script, not by `SqlSink`.
