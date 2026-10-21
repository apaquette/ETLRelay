"""Validate the built ETLRelay wheel and source distribution."""

import configparser
import re
import sys
import tarfile
import tomllib
import zipfile
from email.parser import Parser
from pathlib import Path

from packaging.requirements import Requirement


def require(condition: bool, message: str) -> None:
    """Fail packaging verification with an actionable diagnostic."""
    if not condition:
        raise SystemExit(f"Distribution verification failed: {message}")


def normalize_name(name: str) -> str:
    """Normalize a Python distribution name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def normalize_python_requirement(requirement: str) -> frozenset[str]:
    """Normalize the ordering of comma-separated Python version constraints."""
    return frozenset(
        constraint.strip() for constraint in requirement.split(",") if constraint.strip()
    )


def normalize_dependencies(requirements: list[str]) -> set[str]:
    """Compare complete requirements, including bounds, extras, and markers."""
    normalized = set()
    for value in requirements:
        requirement = Requirement(value)
        normalized.add(normalize_name(requirement.name) + str(requirement)[len(requirement.name) :])
    return normalized


def verify_dependencies(declared: list[str], packaged: list[str], artifact: str) -> None:
    """Reject missing, extra, or altered runtime requirements."""
    require(
        normalize_dependencies(declared) == normalize_dependencies(packaged),
        f"{artifact} runtime dependency requirements differ from pyproject.toml.",
    )


def read_metadata(text: str):
    """Parse Python core distribution metadata."""
    return Parser().parsestr(text)


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]

    name = normalize_name(project["name"])
    version = project["version"]
    python_requirement = project["requires-python"]

    dist_dir = project_root / "dist"

    wheels = sorted(dist_dir.glob(f"{name}-{version}-*.whl"))
    sdists = sorted(dist_dir.glob(f"{name}-{version}.tar.gz"))

    require(len(wheels) == 1, "Expected exactly one matching wheel.")
    require(len(sdists) == 1, "Expected exactly one matching sdist.")

    # Compare the packaged modules with the source tree. This catches
    # missing modules even when the remaining package can still import.
    package_source = project_root / "src" / "etlrelay"
    require(package_source.is_dir(), "Source package directory is missing.")

    source_modules = {
        f"etlrelay/{path.relative_to(package_source).as_posix()}"
        for path in package_source.rglob("*.py")
    }
    require(bool(source_modules), "No Python source modules found.")

    # Verify the wheel.
    with zipfile.ZipFile(wheels[0]) as wheel:
        require(wheel.testzip() is None, "Wheel contains a corrupt entry.")

        entries = set(wheel.namelist())
        dist_info = f"{name}-{version}.dist-info"

        required_metadata = {
            f"{dist_info}/METADATA",
            f"{dist_info}/WHEEL",
            f"{dist_info}/RECORD",
            f"{dist_info}/entry_points.txt",
            f"{dist_info}/licenses/LICENSE",
            f"{dist_info}/licenses/NOTICE",
        }
        require(
            required_metadata <= entries,
            f"Wheel is missing: {sorted(required_metadata - entries)}",
        )

        require(
            source_modules <= entries,
            f"Wheel is missing source modules: {sorted(source_modules - entries)}",
        )

        metadata = read_metadata(wheel.read(f"{dist_info}/METADATA").decode("utf-8"))

        require(
            normalize_name(metadata["Name"]) == name,
            "Wheel distribution name does not match pyproject.toml.",
        )
        require(
            metadata["Version"] == version,
            "Wheel version does not match pyproject.toml.",
        )
        require(
            normalize_python_requirement(metadata["Requires-Python"])
            == normalize_python_requirement(python_requirement),
            "Wheel Python requirement differs from pyproject.toml.",
        )

        verify_dependencies(project["dependencies"], metadata.get_all("Requires-Dist", []), "Wheel")

        entry_points = configparser.ConfigParser()
        entry_points.read_string(wheel.read(f"{dist_info}/entry_points.txt").decode("utf-8"))

        require(
            entry_points.has_section("console_scripts"),
            "Wheel does not declare console scripts.",
        )

        for command, target in project.get("scripts", {}).items():
            require(
                entry_points.get("console_scripts", command, fallback=None) == target,
                f"Console entry point {command!r} is missing or incorrect.",
            )

    print(f"Wheel verified: {wheels[0].name}")

    # Verify the source distribution.
    with tarfile.open(sdists[0], "r:gz") as sdist:
        entries = {member.name for member in sdist.getmembers() if member.isfile()}

        prefix = f"{name}-{version}/"

        required_files = {
            f"{prefix}pyproject.toml",
            f"{prefix}README.md",
            f"{prefix}PKG-INFO",
            f"{prefix}LICENSE",
            f"{prefix}NOTICE",
        }
        required_modules = {f"{prefix}src/{module}" for module in source_modules}

        missing = (required_files | required_modules) - entries

        require(
            not missing,
            f"Source distribution is missing: {sorted(missing)}",
        )

        pkg_info_file = sdist.extractfile(f"{prefix}PKG-INFO")

        if pkg_info_file is None:
            raise SystemExit("Distribution verification failed: Cannot read sdist PKG-INFO.")

        with pkg_info_file:
            metadata = read_metadata(pkg_info_file.read().decode("utf-8"))

        require(
            normalize_name(metadata["Name"]) == name,
            "Sdist distribution name does not match pyproject.toml.",
        )
        require(
            metadata["Version"] == version,
            "Sdist version does not match pyproject.toml.",
        )
        require(
            normalize_python_requirement(metadata["Requires-Python"])
            == normalize_python_requirement(python_requirement),
            "Sdist Python requirement differs from pyproject.toml.",
        )
        verify_dependencies(project["dependencies"], metadata.get_all("Requires-Dist", []), "Sdist")

    print(f"Source distribution verified: {sdists[0].name}")
    print(f"Verified {len(source_modules)} packaged Python modules.")
    print("Distribution metadata and package contents are consistent.")


if __name__ == "__main__":
    sys.exit(main())
