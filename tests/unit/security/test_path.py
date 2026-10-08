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

    def test_path_validator_accepts_explicit_base_path(self, tmp_path: Path):
        base_path = tmp_path

        validator = PathValidator(base_path=base_path)

        assert validator.base_path == base_path.resolve()

    def test_path_validator_resolves_relative_base_path(self, tmp_path: Path):
        base_path = Path("test_data")
        expected_path = (tmp_path / base_path).resolve()

        # Keep the relative path inside the temporary working directory.
        validator = PathValidator(base_path=expected_path)

        assert validator.base_path == expected_path


    # -------------------------------------------------------------------------
    # Valid paths with default base directory
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "relative_path",
        [
            Path("file.txt"),
            Path("subdir/file.txt"),
            Path("subdir/nested/file.txt"),
        ],
    )
    def test_path_validator_accepts_existing_path_inside_working_directory(
        self,
        relative_path: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.chdir(tmp_path)

        candidate_path = tmp_path / relative_path

        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.touch()

        validator = PathValidator()

        result = validator.validate(relative_path)

        assert result == candidate_path.resolve()

    def test_path_validator_accepts_working_directory_itself(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.chdir(tmp_path)

        validator = PathValidator()

        result = validator.validate(Path("."))

        assert result == tmp_path.resolve()


    # -------------------------------------------------------------------------
    # Valid paths with explicit base directory
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "relative_path",
        [
            Path("file.txt"),
            Path("subdir/file.txt"),
            Path("subdir/nested/file.txt"),
        ],
    )
    def test_path_validator_accepts_existing_path_inside_explicit_base(
        self,
        relative_path: Path,
        tmp_path: Path,
    ):
        base_path = tmp_path
        candidate_path = base_path / relative_path

        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.touch()

        validator = PathValidator(base_path=base_path)

        result = validator.validate(relative_path)

        assert result == candidate_path.resolve()

    def test_path_validator_accepts_explicit_base_directory_itself(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path

        validator = PathValidator(base_path=base_path)

        result = validator.validate(Path("."))

        assert result == base_path.resolve()


    # -------------------------------------------------------------------------
    # Non-existent paths
    # -------------------------------------------------------------------------

    def test_path_validator_rejects_nonexistent_path_inside_working_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.chdir(tmp_path)

        validator = PathValidator()

        candidate_path = Path("does_not_exist/file.txt")

        with pytest.raises(PathValidationError):
            validator.validate(candidate_path)

    def test_path_validator_rejects_nonexistent_path_inside_explicit_base(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path

        validator = PathValidator(base_path=base_path)

        candidate_path = Path("does_not_exist/file.txt")

        with pytest.raises(PathValidationError):
            validator.validate(candidate_path)


    # -------------------------------------------------------------------------
    # Paths outside default working-directory boundary
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "candidate_path",
        [
            Path("../outside/file.txt"),
            Path("../../outside/file.txt"),
            Path("../file.txt"),
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

        working_dir.mkdir()
        outside_dir.mkdir()

        outside_path = outside_dir / "outside.txt"
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
        ],
    )
    def test_path_validator_rejects_paths_outside_explicit_base(
        self,
        candidate_path: Path,
        tmp_path: Path,
    ):
        base_path = tmp_path

        validator = PathValidator(base_path=base_path)

        with pytest.raises(PathValidationError):
            validator.validate(candidate_path)

    def test_path_validator_rejects_absolute_path_outside_explicit_base(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path / "base"
        outside_path = tmp_path / "outside.txt"

        base_path.mkdir()
        outside_path.touch()

        validator = PathValidator(base_path=base_path)

        with pytest.raises(PathValidationError):
            validator.validate(outside_path)


    # -------------------------------------------------------------------------
    # Traversal edge cases
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "candidate_path",
        [
            Path("subdir/../file.txt"),
            Path("./file.txt"),
            Path("./subdir/../file.txt"),
        ],
    )
    def test_path_validator_resolves_dot_segments_inside_boundary(
        self,
        candidate_path: Path,
        tmp_path: Path,
    ):
        base_path = tmp_path
        expected_path = base_path / "file.txt"
        expected_path.touch()

        validator = PathValidator(base_path=base_path)

        result = validator.validate(candidate_path)

        assert result == expected_path.resolve()

    @pytest.mark.parametrize(
        "candidate_path",
        [
            Path("subdir/../../../outside/file.txt"),
            Path("./../../outside/file.txt"),
            Path("subdir/../../../../outside/file.txt"),
        ],
    )
    def test_path_validator_rejects_traversal_that_escapes_boundary(
        self,
        candidate_path: Path,
        tmp_path: Path,
    ):
        base_path = tmp_path

        validator = PathValidator(base_path=base_path)

        with pytest.raises(PathValidationError):
            validator.validate(candidate_path)


    # -------------------------------------------------------------------------
    # Boundary-name edge cases
    # -------------------------------------------------------------------------

    def test_path_validator_does_not_confuse_similar_directory_names(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path / "data"
        similar_path = tmp_path / "data-other"

        base_path.mkdir()
        similar_path.mkdir()

        candidate_path = similar_path / "file.txt"
        candidate_path.touch()

        validator = PathValidator(base_path=base_path)

        with pytest.raises(PathValidationError):
            validator.validate(candidate_path)


    # -------------------------------------------------------------------------
    # Explicit base outside current working directory
    # -------------------------------------------------------------------------

    def test_path_validator_allows_explicit_base_outside_working_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        working_dir = tmp_path / "working"
        base_path = tmp_path / "external"
        candidate_path = base_path / "file.txt"

        working_dir.mkdir()
        base_path.mkdir()
        candidate_path.touch()

        monkeypatch.chdir(working_dir)

        validator = PathValidator(base_path=base_path)

        result = validator.validate(Path("file.txt"))

        assert result == candidate_path.resolve()


    # -------------------------------------------------------------------------
    # Absolute paths inside boundary
    # -------------------------------------------------------------------------

    def test_path_validator_accepts_absolute_path_inside_explicit_base(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path
        candidate_path = base_path / "file.txt"
        candidate_path.touch()

        validator = PathValidator(base_path=base_path)

        result = validator.validate(candidate_path)

        assert result == candidate_path.resolve()


    # -------------------------------------------------------------------------
    # String path support tests
    # -------------------------------------------------------------------------

    def test_path_validator_accepts_existing_string_path(self, tmp_path: Path):
        base_path = tmp_path
        candidate_path = base_path / "file.txt"
        candidate_path.touch()

        validator = PathValidator(base_path=base_path)

        result = validator.validate("file.txt")

        assert result == candidate_path.resolve()

    def test_path_validator_accepts_existing_nested_string_path(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path
        candidate_path = base_path / "subdir" / "file.txt"

        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.touch()

        validator = PathValidator(base_path=base_path)

        result = validator.validate("subdir/file.txt")

        assert result == candidate_path.resolve()

    def test_path_validator_accepts_string_path_with_safe_dot_segments(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path
        candidate_path = base_path / "file.txt"
        candidate_path.touch()

        validator = PathValidator(base_path=base_path)

        result = validator.validate("subdir/../file.txt")

        assert result == candidate_path.resolve()

    @pytest.mark.parametrize(
        "candidate_path",
        [
            "../outside/file.txt",
            "subdir/../../outside/file.txt",
            "./../../outside/file.txt",
            "subdir/../../../outside/file.txt",
        ],
    )
    def test_path_validator_rejects_string_path_outside_base(
        self,
        candidate_path: str,
        tmp_path: Path,
    ):
        base_path = tmp_path
        validator = PathValidator(base_path=base_path)

        with pytest.raises(PathValidationError):
            validator.validate(candidate_path)

    def test_path_validator_accepts_absolute_string_path_inside_base(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path
        candidate_path = base_path / "file.txt"
        candidate_path.touch()

        validator = PathValidator(base_path=base_path)

        result = validator.validate(str(candidate_path))

        assert result == candidate_path.resolve()

    def test_path_validator_rejects_absolute_string_path_outside_base(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path / "base"
        outside_dir = tmp_path / "outside"
        candidate_path = outside_dir / "file.txt"

        base_path.mkdir()
        outside_dir.mkdir()
        candidate_path.touch()

        validator = PathValidator(base_path=base_path)

        with pytest.raises(PathValidationError):
            validator.validate(str(candidate_path))

    def test_path_validator_rejects_nonexistent_string_path(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path
        validator = PathValidator(base_path=base_path)

        with pytest.raises(PathValidationError):
            validator.validate("does_not_exist/file.txt")

    def test_path_validator_accepts_string_path_with_default_base(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ):
        candidate_path = tmp_path / "test_file.txt"
        candidate_path.touch()

        monkeypatch.chdir(tmp_path)

        validator = PathValidator()

        result = validator.validate("test_file.txt")

        assert result == candidate_path.resolve()


    # -------------------------------------------------------------------------
    # Edge test cases
    # -------------------------------------------------------------------------

    def test_path_validator_accepts_base_directory(self, tmp_path: Path):
        base_path = tmp_path

        validator = PathValidator(base_path=base_path)

        result = validator.validate(".")

        assert result == base_path.resolve()

    def test_path_validator_accepts_existing_nested_directory(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path
        nested_path = base_path / "subdir" / "nested"

        nested_path.mkdir(parents=True)

        validator = PathValidator(base_path=base_path)

        result = validator.validate("subdir/nested")

        assert result == nested_path.resolve()

    def test_path_validator_accepts_multiple_safe_dot_segments(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path
        candidate_path = base_path / "file.txt"
        candidate_path.touch()

        validator = PathValidator(base_path=base_path)

        result = validator.validate("subdir/nested/../../file.txt")

        assert result == candidate_path.resolve()

    def test_path_validator_rejects_similar_directory_name_outside_base(
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

    def test_path_validator_accepts_absolute_path_inside_base(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path
        candidate_path = base_path / "file.txt"
        candidate_path.touch()

        validator = PathValidator(base_path=base_path)

        result = validator.validate(candidate_path)

        assert result == candidate_path.resolve()

    def test_path_validator_rejects_absolute_path_outside_base(
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

    def test_path_validator_rejects_symlink_resolving_outside_base(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path / "base"
        outside_dir = tmp_path / "outside"

        base_path.mkdir()
        outside_dir.mkdir()

        outside_file = outside_dir / "secret.txt"
        outside_file.touch()

        symlink = base_path / "link.txt"
        symlink.symlink_to(outside_file)

        validator = PathValidator(base_path=base_path)

        with pytest.raises(PathValidationError):
            validator.validate("link.txt")

    def test_path_validator_accepts_symlink_resolving_inside_base(
        self,
        tmp_path: Path,
    ):
        base_path = tmp_path

        target = base_path / "file.txt"
        target.touch()

        symlink = base_path / "link.txt"
        symlink.symlink_to(target)

        validator = PathValidator(base_path=base_path)

        result = validator.validate("link.txt")

        assert result == target.resolve()