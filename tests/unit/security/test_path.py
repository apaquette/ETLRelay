from pathlib import Path

import pytest

from flowforge.security.path import PathValidationError, PathValidator


class TestPathValidator:
    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def test_path_validator_defaults_base_to_current_working_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.chdir(tmp_path)

        validator = PathValidator()

        assert validator.base_path == tmp_path.resolve()

    def test_path_validator_accepts_explicit_base_path(
        self,
        tmp_path: Path,
    ):
        validator = PathValidator(base_path=tmp_path)

        assert validator.base_path == tmp_path.resolve()

    def test_path_validator_resolves_relative_base_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.chdir(tmp_path)

        base_path = Path("test_data")
        base_path.mkdir()

        validator = PathValidator(base_path=base_path)

        assert validator.base_path == (tmp_path / base_path).resolve()

    # -------------------------------------------------------------------------
    # Valid paths inside boundary
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "candidate_path",
        [
            Path("file.txt"),
            Path("subdir/file.txt"),
            Path("subdir/nested/file.txt"),
        ],
    )
    def test_path_validator_accepts_path_inside_working_directory(
        self,
        candidate_path: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.chdir(tmp_path)

        validator = PathValidator()

        expected_path = (tmp_path / candidate_path).resolve()

        result = validator.validate(candidate_path)

        assert result == expected_path

    @pytest.mark.parametrize(
        "candidate_path",
        [
            Path("file.txt"),
            "file.txt",
            Path("subdir/file.txt"),
            "subdir/file.txt",
            Path("subdir/nested/file.txt"),
            "subdir/nested/file.txt",
        ],
    )
    def test_path_validator_accepts_path_inside_explicit_base(
        self,
        candidate_path: Path | str,
        tmp_path: Path,
    ):
        validator = PathValidator(base_path=tmp_path)

        expected_path = (tmp_path / Path(candidate_path)).resolve()

        result = validator.validate(candidate_path)

        assert result == expected_path

    def test_path_validator_accepts_base_directory(
        self,
        tmp_path: Path,
    ):
        validator = PathValidator(base_path=tmp_path)

        result = validator.validate(".")

        assert result == tmp_path.resolve()

    def test_path_validator_accepts_absolute_path_inside_base(
        self,
        tmp_path: Path,
    ):
        candidate_path = tmp_path / "file.txt"

        validator = PathValidator(base_path=tmp_path)

        result = validator.validate(candidate_path)

        assert result == candidate_path.resolve()

    def test_path_validator_allows_explicit_base_outside_working_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        working_dir = tmp_path / "working"
        base_path = tmp_path / "external"

        working_dir.mkdir()
        base_path.mkdir()

        monkeypatch.chdir(working_dir)

        validator = PathValidator(base_path=base_path)

        result = validator.validate("file.txt")

        assert result == (base_path / "file.txt").resolve()

    # -------------------------------------------------------------------------
    # Dot-segment normalization
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "candidate_path",
        [
            Path("subdir/../file.txt"),
            Path("./file.txt"),
            Path("./subdir/../file.txt"),
            Path("subdir/nested/../../file.txt"),
        ],
    )
    def test_path_validator_resolves_dot_segments_inside_boundary(
        self,
        candidate_path: Path,
        tmp_path: Path,
    ):
        validator = PathValidator(base_path=tmp_path)

        expected_path = (tmp_path / "file.txt").resolve()

        result = validator.validate(candidate_path)

        assert result == expected_path

    # -------------------------------------------------------------------------
    # Non-existent paths
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "candidate_path",
        [
            Path("file.txt"),
            Path("subdir/file.txt"),
            Path("subdir/nested/file.txt"),
            "file.txt",
            "subdir/file.txt",
            "subdir/nested/file.txt",
        ],
    )
    def test_path_validator_accepts_nonexistent_path_inside_base(
        self,
        candidate_path: Path | str,
        tmp_path: Path,
    ):
        validator = PathValidator(base_path=tmp_path)

        expected_path = (tmp_path / Path(candidate_path)).resolve()

        assert not expected_path.exists()

        result = validator.validate(candidate_path)

        assert result == expected_path

    # -------------------------------------------------------------------------
    # Paths outside default working-directory boundary
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "candidate_path",
        [
            Path("../outside/file.txt"),
            Path("../../outside/file.txt"),
            Path("../file.txt"),
            Path("subdir/../../outside/file.txt"),
            Path("subdir/../../../outside/file.txt"),
        ],
    )
    def test_path_validator_rejects_paths_outside_working_directory(
        self,
        candidate_path: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.chdir(tmp_path)

        validator = PathValidator()

        with pytest.raises(PathValidationError):
            validator.validate(candidate_path)

    def test_path_validator_rejects_absolute_path_outside_working_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        working_dir = tmp_path / "working"
        outside_dir = tmp_path / "outside"
        outside_path = outside_dir / "outside.txt"

        working_dir.mkdir()
        outside_dir.mkdir()
        outside_path.touch()

        monkeypatch.chdir(working_dir)

        validator = PathValidator()

        with pytest.raises(PathValidationError):
            validator.validate(outside_path)

    # -------------------------------------------------------------------------
    # Paths outside explicit base-directory boundary
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "candidate_path",
        [
            Path("../outside/file.txt"),
            Path("../../outside/file.txt"),
            Path("../file.txt"),
            Path("subdir/../../outside/file.txt"),
            Path("subdir/../../../outside/file.txt"),
        ],
    )
    def test_path_validator_rejects_paths_outside_explicit_base(
        self,
        candidate_path: Path,
        tmp_path: Path,
    ):
        validator = PathValidator(base_path=tmp_path)

        with pytest.raises(PathValidationError):
            validator.validate(candidate_path)

    def test_path_validator_rejects_absolute_path_outside_explicit_base(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path / "base"
        outside_path = tmp_path / "outside" / "file.txt"

        base_path.mkdir()
        outside_path.parent.mkdir()
        outside_path.touch()

        validator = PathValidator(base_path=base_path)

        with pytest.raises(PathValidationError):
            validator.validate(outside_path)

    # -------------------------------------------------------------------------
    # Boundary-name edge cases
    # -------------------------------------------------------------------------

    def test_path_validator_does_not_confuse_similar_directory_names(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path / "data"
        outside_path = tmp_path / "data-other" / "file.txt"

        base_path.mkdir()
        outside_path.parent.mkdir()
        outside_path.touch()

        validator = PathValidator(base_path=base_path)

        with pytest.raises(PathValidationError):
            validator.validate(outside_path)

    # -------------------------------------------------------------------------
    # Symlink edge cases
    # -------------------------------------------------------------------------

    def test_path_validator_rejects_symlink_resolving_outside_base(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path / "base"
        outside_dir = tmp_path / "outside"
        outside_file = outside_dir / "secret.txt"

        base_path.mkdir()
        outside_dir.mkdir()
        outside_file.touch()

        symlink = base_path / "link.txt"
        symlink.symlink_to(outside_file)

        validator = PathValidator(base_path=base_path)

        with pytest.raises(PathValidationError):
            validator.validate(symlink)

    def test_path_validator_accepts_symlink_resolving_inside_base(
        self,
        tmp_path: Path,
    ):
        target = tmp_path / "file.txt"
        target.touch()

        symlink = tmp_path / "link.txt"
        symlink.symlink_to(target)

        validator = PathValidator(base_path=tmp_path)

        result = validator.validate(symlink)

        assert result == target.resolve()