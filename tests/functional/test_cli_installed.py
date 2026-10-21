"""Functional tests for the installed ETLRelay command-line application."""

from __future__ import annotations

import ast
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import pytest
import yaml

_SECRET_SENTINEL = "ETLRELAY_SECRET_SENTINEL_7F31A9"
_PAYLOAD_SENTINEL = "ETLRELAY_PAYLOAD_SENTINEL_C84D21"


def _subprocess_environment(
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    """Create an environment isolated from the development checkout."""
    env = os.environ.copy()

    for name in (
        "PYTHONHOME",
        "PYTHONPATH",
        "PYTHONUSERBASE",
        "VIRTUAL_ENV",
        "UV_PROJECT_ENVIRONMENT",
    ):
        env.pop(name, None)

    env["PYTHONNOUSERSITE"] = "1"

    if overrides:
        env.update(overrides)

    return env


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command with captured standard output and error."""
    return subprocess.run(
        command,
        cwd=cwd,
        env=_subprocess_environment(env),
        capture_output=True,
        check=False,
        text=True,
        timeout=120,
    )


@pytest.fixture(scope="session")
def installed_cli(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Build and install ETLRelay into an isolated virtual environment.

    Returns:
        Path to the installed ``etlrelay`` console-script executable.

    Raises:
        AssertionError: If building, installing, or importing the installed
            package fails.
    """
    project_root = Path(__file__).resolve().parents[2]
    uv = shutil.which("uv")
    assert uv is not None, "The functional package tests require uv."

    artifact_dir = tmp_path_factory.mktemp("etlrelay-artifacts")
    outside_checkout = tmp_path_factory.mktemp("etlrelay-install-work")
    wheel_dir = artifact_dir / "wheel"
    wheel_dir.mkdir()

    build = _run(
        [
            uv,
            "build",
            "--wheel",
            "--out-dir",
            str(wheel_dir),
        ],
        cwd=project_root,
    )
    assert build.returncode == 0, (
        f"Wheel build failed.\nstdout:\n{build.stdout}\nstderr:\n{build.stderr}"
    )

    wheels = list(wheel_dir.glob("etlrelay-*.whl"))
    assert len(wheels) == 1, f"Expected one ETLRelay wheel, found {wheels}."
    wheel = wheels[0]

    requirements_file = artifact_dir / "runtime-requirements.txt"
    export = _run(
        [
            uv,
            "export",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--output-file",
            str(requirements_file),
        ],
        cwd=project_root,
    )
    assert export.returncode == 0, (
        f"Exporting locked runtime dependencies failed.\n"
        f"stdout:\n{export.stdout}\nstderr:\n{export.stderr}"
    )

    venv_dir = artifact_dir / "venv"
    create_venv = _run(
        [
            uv,
            "venv",
            "--python",
            sys.executable,
            str(venv_dir),
        ],
        cwd=outside_checkout,
    )
    assert create_venv.returncode == 0, (
        f"Creating the test virtual environment failed.\n"
        f"stdout:\n{create_venv.stdout}\nstderr:\n{create_venv.stderr}"
    )

    scripts_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    python = scripts_dir / ("python.exe" if os.name == "nt" else "python")
    executable = scripts_dir / ("etlrelay.exe" if os.name == "nt" else "etlrelay")

    install_dependencies = _run(
        [
            uv,
            "pip",
            "sync",
            "--python",
            str(python),
            str(requirements_file),
        ],
        cwd=outside_checkout,
    )
    assert install_dependencies.returncode == 0, (
        f"Installing locked runtime dependencies failed.\n"
        f"stdout:\n{install_dependencies.stdout}\n"
        f"stderr:\n{install_dependencies.stderr}"
    )

    install_wheel = _run(
        [
            uv,
            "pip",
            "install",
            "--python",
            str(python),
            "--no-deps",
            str(wheel),
        ],
        cwd=outside_checkout,
    )
    assert install_wheel.returncode == 0, (
        f"Installing the built ETLRelay wheel failed.\n"
        f"stdout:\n{install_wheel.stdout}\n"
        f"stderr:\n{install_wheel.stderr}"
    )
    assert executable.is_file(), f"Installed console script was not created: {executable}"

    # Verify that imports resolve from the installed virtual environment,
    # not from the repository checkout.
    inspection = _run(
        [
            str(python),
            "-c",
            "import etlrelay; print(etlrelay.__file__)",
        ],
        cwd=outside_checkout,
    )
    assert inspection.returncode == 0, (
        f"Importing the installed package failed.\n"
        f"stdout:\n{inspection.stdout}\n"
        f"stderr:\n{inspection.stderr}"
    )

    package_file = Path(inspection.stdout.strip()).resolve()
    assert package_file.is_relative_to(venv_dir.resolve()), (
        f"ETLRelay imported from outside the test environment: {package_file}"
    )
    assert not package_file.is_relative_to(project_root.resolve()), (
        f"ETLRelay unexpectedly imported from the repository: {package_file}"
    )

    return executable


def _write_config(work_dir: Path, config: dict[str, Any]) -> Path:
    """Write a YAML pipeline configuration into a temporary directory."""
    config_path = work_dir / "pipeline.yml"
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )
    return config_path


def _file_pipeline_config(
    work_dir: Path,
    *,
    source_path: str = "input.csv",
    sink_path: str = "output.csv",
    processors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a local-file CSV pipeline using the supported YAML schema."""
    storage = {
        "type": "local",
        "base_path": str(work_dir.resolve()),
    }

    return {
        "version": 1,
        "source": {
            "type": "file",
            "path": source_path,
            "format": "csv",
            "storage": storage,
        },
        "processors": [] if processors is None else processors,
        "sink": {
            "type": "file",
            "path": sink_path,
            "format": "csv",
            "storage": storage,
        },
    }


def test_installed_cli_help(installed_cli: Path, tmp_path: Path) -> None:
    """Show general help successfully through the installed executable."""
    result = _run([str(installed_cli), "--help"], cwd=tmp_path)

    assert result.returncode == 0
    assert "Run and validate ETLRelay pipelines" in result.stdout
    assert "run" in result.stdout
    assert "validate" in result.stdout
    assert "version" in result.stdout
    assert result.stderr == ""


def test_installed_cli_command_help(
    installed_cli: Path,
    tmp_path: Path,
) -> None:
    """Show help for an individual command."""
    result = _run(
        [str(installed_cli), "help", "run"],
        cwd=tmp_path,
    )

    assert result.returncode == 0
    assert "PIPELINE" in result.stdout
    assert "YAML" in result.stdout
    assert result.stderr == ""


def test_installed_cli_version(
    installed_cli: Path,
    tmp_path: Path,
) -> None:
    """Print installed package version metadata."""
    result = _run(
        [str(installed_cli), "version"],
        cwd=tmp_path,
    )

    assert result.returncode == 0
    assert result.stdout.startswith("etlrelay ")
    assert result.stdout.strip().split(maxsplit=1)[1]
    assert result.stderr == ""


def test_installed_cli_missing_argument_is_usage_error(
    installed_cli: Path,
    tmp_path: Path,
) -> None:
    """Return the documented usage-error exit code for a missing argument."""
    result = _run([str(installed_cli), "run"], cwd=tmp_path)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "PIPELINE" in result.stderr
    assert "Usage:" in result.stderr


def test_installed_cli_unknown_help_command_is_usage_error(
    installed_cli: Path,
    tmp_path: Path,
) -> None:
    """Report an unknown help target as a usage error."""
    result = _run(
        [str(installed_cli), "help", "unknown-command"],
        cwd=tmp_path,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "Unknown command" in result.stderr


def test_installed_cli_validate_success_does_not_execute_pipeline(
    installed_cli: Path,
    tmp_path: Path,
) -> None:
    """Validate a pipeline without running its processor or creating output."""
    (tmp_path / "input.csv").write_text(
        "id\n1\n",
        encoding="utf-8",
    )
    config = _file_pipeline_config(
        tmp_path,
        processors=[
            {"type": "select_columns", "columns": ["missing_column"]},
        ],
    )
    config_path = _write_config(tmp_path, config)
    output_path = tmp_path / "output.csv"

    result = _run(
        [str(installed_cli), "validate", str(config_path)],
        cwd=tmp_path,
    )

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert f"Pipeline configuration is valid: {config_path}" in result.stdout
    assert result.stderr == ""
    assert not output_path.exists()


def test_installed_cli_validate_invalid_yaml_returns_code_3(
    installed_cli: Path,
    tmp_path: Path,
) -> None:
    """Report malformed YAML using the validation-error exit code."""
    config_path = tmp_path / "invalid.yml"
    config_path.write_text(
        f"version: [\n# {_SECRET_SENTINEL}\n",
        encoding="utf-8",
    )

    result = _run(
        [str(installed_cli), "validate", str(config_path)],
        cwd=tmp_path,
    )

    assert result.returncode == 3
    assert result.stdout == ""
    assert "Invalid YAML syntax" in result.stderr
    assert _SECRET_SENTINEL not in result.stdout + result.stderr


def test_installed_cli_validate_invalid_configuration_returns_code_3(
    installed_cli: Path,
    tmp_path: Path,
) -> None:
    """Return the validation-error exit code for an invalid schema."""
    config_path = _write_config(
        tmp_path,
        {
            "version": 999,
            "source": {},
            "processors": [],
            "sink": {},
        },
    )

    result = _run(
        [str(installed_cli), "validate", str(config_path)],
        cwd=tmp_path,
    )

    assert result.returncode == 3
    assert result.stdout == ""
    assert "Invalid pipeline configuration" in result.stderr


def test_installed_cli_run_executes_csv_pipeline(
    installed_cli: Path,
    tmp_path: Path,
) -> None:
    """Execute a CSV pipeline and verify its actual output file."""
    (tmp_path / "input.csv").write_text(
        "id,amount,state\n1,10,ready\n2,-2,skip\n",
        encoding="utf-8",
    )
    config = _file_pipeline_config(
        tmp_path,
        processors=[
            {"type": "select_columns", "columns": ["id", "amount"]},
            {
                "type": "filter_rows",
                "column": "amount",
                "operator": ">",
                "value": 0,
            },
            {"type": "rename_columns", "mapping": {"id": "record_id"}},
        ],
    )
    config_path = _write_config(tmp_path, config)
    output_path = tmp_path / "output.csv"

    result = _run(
        [str(installed_cli), "run", str(config_path)],
        cwd=tmp_path,
    )

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert f"Pipeline completed: {config_path}" in result.stdout
    assert result.stderr == ""
    assert output_path.read_text(encoding="utf-8") == ('"record_id","amount"\n1,10\n')


@pytest.mark.parametrize(("source_kind", "sink_kind"), [("parquet", "sql"), ("sql", "parquet")])
def test_installed_cli_runs_processed_parquet_sql_pipeline(
    installed_cli: Path,
    tmp_path: Path,
    source_kind: str,
    sink_kind: str,
) -> None:
    """Verify both non-CSV boundaries through the installed YAML CLI."""
    records = [
        {"id": 1, "amount": 5.5, "label": "alpha"},
        {"id": 2, "amount": None, "label": "beta"},
        {"id": 3, "amount": 25.5, "label": "gamma"},
    ]
    config = _file_pipeline_config(
        tmp_path,
        processors=[
            {"type": "select_columns", "columns": ["id", "amount"]},
            {"type": "rename_columns", "mapping": {"id": "record_id"}},
            # The renamed field makes processor order observable.
            {"type": "filter_rows", "column": "record_id", "operator": ">", "value": 1},
        ],
    )
    environment: dict[str, str] = {}
    if source_kind == "parquet":
        pq.write_table(
            pa.Table.from_pylist(
                records,
                schema=pa.schema(
                    [
                        pa.field("id", pa.int64(), nullable=False),
                        pa.field("amount", pa.float64(), nullable=True),
                        pa.field("label", pa.string(), nullable=False),
                    ]
                ),
            ),
            tmp_path / "input.parquet",
        )
        config["source"].update(path="input.parquet", format="parquet")
    else:
        with sqlite3.connect(tmp_path / "source.db") as connection:
            connection.execute("CREATE TABLE source_records (id INTEGER, amount REAL, label TEXT)")
            connection.executemany(
                "INSERT INTO source_records VALUES (:id, :amount, :label)", records
            )
        environment["ETLRELAY_TEST_SOURCE_URL"] = f"sqlite:///{tmp_path / 'source.db'}"
        config["source"] = {
            "type": "sql",
            "connection_url_env": "ETLRELAY_TEST_SOURCE_URL",
            "query": "SELECT id, amount, label FROM source_records WHERE id >= :first ORDER BY id",
            "parameters": {"first": 1},
        }

    if sink_kind == "sql":
        with sqlite3.connect(tmp_path / "sink.db") as connection:
            connection.execute(
                "CREATE TABLE processed_records (record_id INTEGER PRIMARY KEY, amount REAL)"
            )
            connection.execute("INSERT INTO processed_records VALUES (0, -1.0)")
        environment["ETLRELAY_TEST_SINK_URL"] = f"sqlite:///{tmp_path / 'sink.db'}"
        config["sink"] = {
            "type": "sql",
            "connection_url_env": "ETLRELAY_TEST_SINK_URL",
            "table_name": "processed_records",
        }
    else:
        config["sink"].update(path="output.parquet", format="parquet")

    config_path = _write_config(tmp_path, config)
    validation = _run(
        [str(installed_cli), "validate", str(config_path)], cwd=tmp_path, env=environment
    )
    assert validation.returncode == 0, (validation.stdout, validation.stderr)
    assert validation.stderr == ""
    if sink_kind == "sql":
        with sqlite3.connect(tmp_path / "sink.db") as connection:
            assert connection.execute("SELECT * FROM processed_records").fetchall() == [(0, -1.0)]
    else:
        assert not (tmp_path / "output.parquet").exists()

    result = _run([str(installed_cli), "run", str(config_path)], cwd=tmp_path, env=environment)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert f"Pipeline completed: {config_path}" in result.stdout
    assert result.stderr == ""

    if sink_kind == "sql":
        with sqlite3.connect(tmp_path / "sink.db") as connection:
            result_rows = connection.execute(
                "SELECT record_id, amount FROM processed_records ORDER BY record_id"
            ).fetchall()
        # Existing rows survive; selected values and nulls are appended.
        assert result_rows == [(0, -1.0), (2, None), (3, 25.5)]
    else:
        table = pq.read_table(tmp_path / "output.parquet")
        assert table.schema.equals(
            pa.schema([pa.field("record_id", pa.int64()), pa.field("amount", pa.float64())]),
            check_metadata=False,
        )
        assert table.to_pylist() == [
            {"record_id": 2, "amount": None},
            {"record_id": 3, "amount": 25.5},
        ]


def test_installed_cli_run_failure_does_not_leak_payload(
    installed_cli: Path,
    tmp_path: Path,
) -> None:
    """Hide sensitive CSV payload values when runtime processing fails."""
    (tmp_path / "input.csv").write_text(
        f"id,payload\n1,{_PAYLOAD_SENTINEL}\n",
        encoding="utf-8",
    )
    config = _file_pipeline_config(
        tmp_path,
        processors=[
            {"type": "select_columns", "columns": ["missing_column"]},
        ],
    )
    config_path = _write_config(tmp_path, config)

    result = _run(
        [str(installed_cli), "run", str(config_path)],
        cwd=tmp_path,
    )
    terminal_output = result.stdout + result.stderr

    assert result.returncode == 4
    assert "Pipeline execution failed" in result.stderr
    assert "Traceback" not in terminal_output
    assert _PAYLOAD_SENTINEL not in terminal_output
    assert _SECRET_SENTINEL not in terminal_output
    assert not (tmp_path / "output.csv").exists()


def test_installed_cli_run_does_not_leak_sql_url_or_query_values(
    installed_cli: Path,
    tmp_path: Path,
) -> None:
    """Hide environment-sourced connection values and SQL payloads on failure."""
    database_path = tmp_path / f"{_SECRET_SENTINEL}.db"
    connection_variable = "ETLRELAY_FUNCTIONAL_SOURCE_DATABASE_URL"
    connection_url = f"sqlite:///{database_path.as_posix()}"

    config = {
        "version": 1,
        "source": {
            "type": "sql",
            "connection_url_env": connection_variable,
            "query": (f"SELECT '{_PAYLOAD_SENTINEL}' AS payload FROM missing_table"),
        },
        "processors": [],
        "sink": {
            "type": "file",
            "path": "output.csv",
            "format": "csv",
            "storage": {
                "type": "local",
                "base_path": str(tmp_path.resolve()),
            },
        },
    }
    config_path = _write_config(tmp_path, config)

    result = _run(
        [str(installed_cli), "run", str(config_path)],
        cwd=tmp_path,
        env={connection_variable: connection_url},
    )
    terminal_output = result.stdout + result.stderr

    assert result.returncode == 4
    assert "Pipeline execution failed" in result.stderr
    assert _SECRET_SENTINEL not in terminal_output
    assert _PAYLOAD_SENTINEL not in terminal_output
    assert connection_url not in terminal_output
    assert not (tmp_path / "output.csv").exists()


def test_installed_candidate_runs_documented_examples(
    installed_cli: Path,
    tmp_path: Path,
) -> None:
    """Execute maintained snippets and example files outside the source checkout."""
    project_root = Path(__file__).resolve().parents[2]
    python = installed_cli.with_name("python.exe" if os.name == "nt" else "python")
    work = tmp_path / "examples-work"
    work.mkdir()
    shutil.copytree(project_root / "examples", work / "examples")

    def run_example(*arguments: str, cwd: Path = work):
        result = _run([str(python), *arguments], cwd=cwd)
        assert result.returncode == 0, (arguments, result.stdout, result.stderr)
        assert result.stderr == ""
        return result

    for name in ("copy_csv", "transform_csv", "parquet_pipeline", "custom_processor"):
        run_example(f"examples/{name}.py")
    sql_result = run_example("examples/sqlite_pipeline.py")
    assert ast.literal_eval(sql_result.stdout.strip()) == [
        {"id": 1, "customer": "Avery", "total": 18.5},
        {"id": 3, "customer": "Jordan", "total": 42.25},
    ]
    data = work / "examples/data"
    assert pacsv.read_csv(data / "copy_output.csv").equals(pacsv.read_csv(data / "input.csv"))
    expected_people = [
        {"customer_name": "Bob", "age": 25},
        {"customer_name": "Charlie", "age": 18},
        {"customer_name": "Evan", "age": 42},
    ]
    assert pacsv.read_csv(data / "transformed.csv").to_pylist() == expected_people
    parquet = pq.read_table(data / "output.parquet")
    assert parquet.to_pylist() == expected_people
    assert parquet.schema == pa.schema([("customer_name", pa.string()), ("age", pa.int64())])
    upper = pacsv.read_csv(data / "uppercase_output.csv").to_pylist()
    assert upper == [
        {"name": row["name"].upper(), "age": row["age"]}
        for row in pacsv.read_csv(data / "input.csv").to_pylist()
    ]

    configuration_data = work / "examples/configuration/data"
    environment = {
        "ETLRELAY_SOURCE_DATABASE_URL": f"sqlite:///{configuration_data / 'source.db'}",
        "ETLRELAY_SINK_DATABASE_URL": f"sqlite:///{configuration_data / 'sink.db'}",
    }
    expected_records = [
        {"record_id": 1, "amount": 18.5},
        {"record_id": 2, "amount": 27.0},
        {"record_id": 3, "amount": 0.0},
    ]

    def assert_output(config: dict[str, Any]) -> None:
        sink = config["sink"]
        if sink["type"] == "file":
            path = work / sink["path"]
            table = pacsv.read_csv(path) if sink["format"] == "csv" else pq.read_table(path)
            assert table.schema == pa.schema([("record_id", pa.int64()), ("amount", pa.float64())])
            assert table.to_pylist() == expected_records
        else:
            with sqlite3.connect(work / "examples/configuration/data/sink.db") as connection:
                rows = connection.execute(
                    "SELECT record_id, amount FROM processed_records ORDER BY record_id"
                ).fetchall()
            assert rows == [(1, 18.5), (2, 27.0), (3, 0.0)]

    configurations = sorted((work / "examples/configuration").glob("*.yaml"))
    assert len(configurations) == 9
    for configuration in configurations:
        run_example("examples/configuration/prepare_demo_data.py")
        config = yaml.safe_load(configuration.read_text(encoding="utf-8"))
        if config["sink"]["type"] == "file":
            (work / config["sink"]["path"]).unlink(missing_ok=True)
        validation = _run(
            [str(installed_cli), "validate", str(configuration)], cwd=work, env=environment
        )
        assert validation.returncode == 0, (validation.stdout, validation.stderr)
        assert validation.stderr == ""
        if config["sink"]["type"] == "file":
            assert not (work / config["sink"]["path"]).exists()
        else:
            with sqlite3.connect(work / "examples/configuration/data/sink.db") as connection:
                assert connection.execute("SELECT COUNT(*) FROM processed_records").fetchone() == (
                    0,
                )
        result = _run([str(installed_cli), "run", str(configuration)], cwd=work, env=environment)
        assert result.returncode == 0, (configuration.name, result.stdout, result.stderr)
        assert result.stderr == ""
        assert_output(config)

    for name in ("csv_to_parquet", "sql_to_sql"):
        run_example("examples/configuration/prepare_demo_data.py")
        configuration = work / f"examples/configuration/{name}.yaml"
        config = yaml.safe_load(configuration.read_text(encoding="utf-8"))
        if config["sink"]["type"] == "file":
            (work / config["sink"]["path"]).unlink(missing_ok=True)
        result = _run(
            [str(python), "examples/configuration/run.py", str(configuration)],
            cwd=work,
            env=environment,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert result.stderr == ""
        assert_output(config)


def test_installed_candidate_runs_quick_start(installed_cli: Path, tmp_path: Path) -> None:
    """Execute the actual quick-start fences against the installed candidate."""
    project_root = Path(__file__).resolve().parents[2]
    python = installed_cli.with_name("python.exe" if os.name == "nt" else "python")
    quickstart = tmp_path / "quickstart"
    quickstart.mkdir()
    guide = (project_root / "docs/getting-started.md").read_text(encoding="utf-8")
    for language, filename in (
        ("csv", "input.csv"),
        ("yaml", "pipeline.yaml"),
        ("python", "pipeline.py"),
    ):
        match = re.search(rf"```{language}\n(.*?)\n```", guide, re.DOTALL)
        assert match is not None, f"Missing quick-start {language} example"
        (quickstart / filename).write_text(match.group(1) + "\n", encoding="utf-8")
    validation = _run([str(installed_cli), "validate", "pipeline.yaml"], cwd=quickstart)
    assert validation.returncode == 0, validation.stderr
    assert not (quickstart / "output.csv").exists()
    result = _run([str(installed_cli), "run", "pipeline.yaml"], cwd=quickstart)
    assert result.returncode == 0, result.stderr
    result = _run([str(python), "pipeline.py"], cwd=quickstart)
    assert result.returncode == 0, result.stderr
    expected = pa.table({"record_id": [1, 3], "amount": [10, 5]})
    assert pacsv.read_csv(quickstart / "output.csv").equals(expected)
    assert pacsv.read_csv(quickstart / "python-output.csv").equals(expected)
