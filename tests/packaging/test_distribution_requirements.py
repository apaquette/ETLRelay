"""Regression checks for the standalone distribution metadata verifier."""

import runpy
from pathlib import Path

import pytest

CHECKS = runpy.run_path(str(Path(__file__).with_name("check_distributions.py")))


@pytest.mark.parametrize("artifact", ["Wheel", "Sdist"])
@pytest.mark.parametrize(
    "packaged",
    [[], ["pyarrow>=23.0.1"], ["pyarrow>=23.0.1,<25"], ["pyarrow>=23.0.1,<24", "polars>=1"]],
    ids=["missing", "missing-upper-bound", "changed-upper-bound", "unexpected-dependency"],
)
def test_metadata_rejects_incomplete_or_changed_requirements(
    artifact: str,
    packaged: list[str],
) -> None:
    with pytest.raises(SystemExit, match=f"{artifact} runtime dependency requirements differ"):
        CHECKS["verify_dependencies"](["pyarrow>=23.0.1,<24"], packaged, artifact)


def test_metadata_accepts_equivalent_requirement_formatting() -> None:
    CHECKS["verify_dependencies"](["Example_Package >= 1, < 2"], ["example-package<2,>=1"], "Wheel")
