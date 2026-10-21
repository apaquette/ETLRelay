"""Smoke-test built ETLRelay distributions across Python versions and platforms."""

import argparse
import csv
import os
import subprocess
import sys
import tempfile
import textwrap
import tomllib
from pathlib import Path


def require(condition: bool, message: str) -> None:
    """Fail with an actionable compatibility diagnostic."""
    if not condition:
        raise SystemExit(f"Compatibility smoke test failed: {message}")


def run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> str:
    """Execute a command and fail when it exits unsuccessfully."""
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        raise SystemExit(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    return result.stdout


def main() -> None:
    """Select built artifacts and test each in a separate clean environment."""
    project_root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", nargs="?", type=Path, default=project_root / "dist")
    parser.add_argument("--artifact", choices=("wheel", "sdist", "both"), default="both")
    arguments = parser.parse_args()
    dist_dir = arguments.dist.resolve()
    expected_version = project["version"]
    artifacts = []
    for kind, pattern in (
        ("wheel", f"etlrelay-{expected_version}-*.whl"),
        ("sdist", f"etlrelay-{expected_version}.tar.gz"),
    ):
        if arguments.artifact not in (kind, "both"):
            continue
        matches = sorted(dist_dir.glob(pattern))
        require(len(matches) == 1, f"Expected one {kind} for {expected_version} in {dist_dir}.")
        artifacts.extend(matches)
    for artifact in artifacts:
        smoke_artifact(project_root, expected_version, artifact)


def smoke_artifact(project_root: Path, expected_version: str, artifact: Path) -> None:
    """Install an archive outside the checkout and exercise public APIs/CLI."""
    env = os.environ.copy()
    for name in (
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONUSERBASE",
        "VIRTUAL_ENV",
        "UV_PROJECT_ENVIRONMENT",
    ):
        env.pop(name, None)
    env["PYTHONNOUSERSITE"] = "1"

    with tempfile.TemporaryDirectory(prefix="etlrelay-compat-") as temp:
        temp_dir = Path(temp).resolve()
        work_dir = temp_dir / "work"
        venv_dir = temp_dir / "venv"
        work_dir.mkdir()

        require(
            not temp_dir.is_relative_to(project_root),
            "Temporary test directory is inside the repository.",
        )

        if os.name == "nt":
            python = venv_dir / "Scripts" / "python.exe"
            cli = venv_dir / "Scripts" / "etlrelay.exe"
        else:
            python = venv_dir / "bin" / "python"
            cli = venv_dir / "bin" / "etlrelay"

        # Build an independent environment with the selected CI interpreter.
        run(
            ["uv", "venv", "--python", sys.executable, str(venv_dir)],
            cwd=work_dir,
            env=env,
        )

        # Install the selected archive; sdist installation uses an isolated build.
        run(
            ["uv", "pip", "install", "--python", str(python), str(artifact)],
            cwd=work_dir,
            env=env,
        )

        run(
            ["uv", "pip", "check", "--python", str(python)],
            cwd=work_dir,
            env=env,
        )

        require(cli.is_file(), "Installed CLI executable is missing.")

        # Verify that Python imports the installed distribution exclusively.
        import_check = textwrap.dedent(
            """
            import sys
            from importlib.metadata import version
            from pathlib import Path

            import etlrelay
            import pyarrow
            from etlrelay.core import (
                Batch, Source, Processor, Sink, TabularReader, TabularWriter,
                KeyValueReader, WriterError,
            )
            from etlrelay.pipeline import Pipeline
            from etlrelay.processors import SelectColumns, RenameColumns, FilterRows
            from etlrelay.readers import CsvReader, ParquetReader, YamlReader, YamlDocumentError
            from etlrelay.writers import CsvWriter, ParquetWriter
            from etlrelay.sources import FileSource, SqlSource
            from etlrelay.sinks import FileSink, SqlSink
            from etlrelay.storage import LocalFileSystem, FileSystem, FileSystemError
            from etlrelay.security import PathValidator, PathValidationError
            from etlrelay.config.loader import ConfigLoader
            from etlrelay.config.pipeline_builder import PipelineBuilder
            from etlrelay.default_components import create_default_component_catalog
            from sqlalchemy import create_engine, text

            expected_version = sys.argv[1]
            checkout = Path(sys.argv[2]).resolve()

            package_path = Path(etlrelay.__file__).resolve()
            environment = Path(sys.prefix).resolve()

            assert package_path.is_relative_to(environment), package_path
            assert not package_path.is_relative_to(checkout), package_path
            assert version("etlrelay") == expected_version

            for entry in sys.path:
                if entry:
                    assert not Path(entry).resolve().is_relative_to(checkout), entry

            # Exercise direct Python composition with native Parquet and SQLite.
            Path("direct-input.csv").write_text("id,amount\\n1,10\\n2,-2\\n", encoding="utf-8")
            storage = LocalFileSystem(PathValidator(Path.cwd()))
            Pipeline(
                FileSource("direct-input.csv", storage, CsvReader()),
                [SelectColumns(["id", "amount"]), FilterRows("amount", ">", 0)],
                FileSink("direct-output.parquet", storage, ParquetWriter()),
            ).run()
            engine = create_engine("sqlite:///:memory:")
            try:
                with engine.begin() as connection:
                    connection.execute(text("CREATE TABLE records (id INTEGER, amount INTEGER)"))
                Pipeline(
                    FileSource("direct-output.parquet", storage, ParquetReader()),
                    [], SqlSink(engine, "records"),
                ).run()
                batches = list(SqlSource(engine, "SELECT id, amount FROM records").read())
                assert len(batches) == 1
                assert batches[0].table.to_pylist() == [{"id": 1, "amount": 10}]
                assert batches[0].table.schema == pyarrow.schema([
                    ("id", pyarrow.int64()), ("amount", pyarrow.int64())
                ])
            finally:
                engine.dispose()

            print(f"Python: {sys.version.split()[0]}")
            print(f"Installed package: {package_path}")
            print(f"ETLRelay version: {version('etlrelay')}")
            """
        )

        print(
            run(
                [
                    str(python),
                    "-I",
                    "-c",
                    import_check,
                    expected_version,
                    str(project_root),
                ],
                cwd=work_dir,
                env=env,
            ),
            end="",
        )

        # Exercise the installed console script.
        version_output = run(
            [str(cli), "version"],
            cwd=work_dir,
            env=env,
        )
        require(
            version_output.strip() == f"etlrelay {expected_version}",
            "Installed CLI version does not match project metadata.",
        )

        help_output = run(
            [str(cli), "--help"],
            cwd=work_dir,
            env=env,
        )
        require(
            all(command in help_output for command in ("run", "validate", "version")),
            "Installed CLI help is missing expected commands.",
        )

        # Exercise YAML validation and a representative pipeline through the installed CLI.
        (work_dir / "input.csv").write_text(
            "id,amount,state\n1,10,ready\n",
            encoding="utf-8",
        )

        (work_dir / "pipeline.yml").write_text(
            textwrap.dedent(
                """\
                version: 1
                source:
                  type: file
                  path: input.csv
                  format: csv
                  storage:
                    type: local
                    base_path: .
                processors:
                  - type: select_columns
                    columns: [id, amount]
                sink:
                  type: file
                  path: output.csv
                  format: csv
                  storage:
                    type: local
                    base_path: .
                """
            ),
            encoding="utf-8",
        )

        run(
            [str(cli), "validate", "pipeline.yml"],
            cwd=work_dir,
            env=env,
        )
        require(
            not (work_dir / "output.csv").exists(),
            "Validation unexpectedly created output.",
        )

        run(
            [str(cli), "run", "pipeline.yml"],
            cwd=work_dir,
            env=env,
        )

        output_path = work_dir / "output.csv"
        require(output_path.is_file(), "Pipeline produced no output.")

        with output_path.open(encoding="utf-8", newline="") as output:
            rows = list(csv.reader(output))

        require(
            rows == [["id", "amount"], ["1", "10"]],
            f"Unexpected pipeline output: {rows!r}",
        )

        print(f"Installed-artifact compatibility smoke test passed: {artifact.name}")


if __name__ == "__main__":
    main()
