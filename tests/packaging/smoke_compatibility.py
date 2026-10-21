"""Smoke-test a built ETLRelay wheel across Python versions and platforms."""

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
    """Install the wheel outside the checkout and exercise its public CLI."""
    project_root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]

    expected_version = project["version"]

    dist_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else project_root / "dist"

    wheels = sorted(dist_dir.glob(f"etlrelay-{expected_version}-*.whl"))

    require(
        len(wheels) == 1,
        (
            f"Expected exactly one wheel for ETLRelay {expected_version} "
            f"in {dist_dir}, found {len(wheels)}. "
            f"Available wheels: {[path.name for path in dist_dir.glob('*.whl')]}"
        ),
    )

    wheel = wheels[0]

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
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

        # Install the built wheel, never the repository or an editable install.
        run(
            ["uv", "pip", "install", "--python", str(python), str(wheel)],
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
            import polars

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

        # Use real supported CSV and processor components from the wheel.
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

        print("Installed-wheel compatibility smoke test passed.")


if __name__ == "__main__":
    main()
