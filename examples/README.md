# Python examples

Use CPython 3.12–3.14 and an installed ETLRelay archive from the same commit as
these examples. Run from a directory containing the copied `examples/` tree;
imports must resolve to the installed package. See `docs/getting-started.md` for
candidate installation.

| Command | Input | Result |
| --- | --- | --- |
| `python examples/copy_csv.py` | Supplied `examples/data/input.csv` | `examples/data/copy_output.csv`, all five rows |
| `python examples/transform_csv.py` | Same CSV | `examples/data/transformed.csv`, Bob/Charlie/Evan with `customer_name` and `age` |
| `python examples/parquet_pipeline.py` | Creates a synthetic Parquet input | `examples/data/output.parquet`, Bob/Charlie/Evan with preserved types |
| `python examples/sqlite_pipeline.py` | Creates in-memory SQLite tables | Prints Avery/Jordan ready orders; disposes the caller-owned engine |
| `python examples/custom_processor.py` | Supplied CSV | `examples/data/uppercase_output.csv`, five rows with uppercase names |

The custom processor is application code used through the existing protocol;
it is not a new built-in YAML component. File examples overwrite their named
demonstration outputs and do not provide atomic replacement.

See [configuration examples](configuration/README.md) for nine YAML pipelines,
SQL environment references, the shared Python runner, and expected output.
