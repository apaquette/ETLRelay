from pathlib import Path
from typing import Any, BinaryIO

import pytest

from etlrelay.security import PathValidationError, PathValidator
from etlrelay.storage import FileSystem, FileSystemError, LocalFileSystem


class TestLocalFileSystem:
    def test_local_filesystem_satisfies_protocol(self):
        file_system = LocalFileSystem(PathValidator())
        assert isinstance(file_system, FileSystem)


class TestLocalFileSystemOpenRead:
    def test_open_read_returns_binary_stream_for_existing_file(
        self,
        tmp_path: Path,
    ):
        # Arrange
        content = b"name,age\nAlice,30\n"
        file_path = tmp_path / "input.csv"
        file_path.write_bytes(content)

        filesystem = LocalFileSystem(path_validator=PathValidator(base_path=tmp_path))

        # Act / Assert
        with filesystem.open_read("input.csv") as stream:
            assert stream.mode == "rb"
            assert stream.read() == content

    def test_open_read_supports_nested_file_path(
        self,
        tmp_path: Path,
    ):
        # Arrange
        nested_dir = tmp_path / "data" / "input"
        nested_dir.mkdir(parents=True)

        file_path = nested_dir / "records.csv"
        file_path.write_bytes(b"id,value\n1,test\n")

        filesystem = LocalFileSystem(path_validator=PathValidator(base_path=tmp_path))

        # Act / Assert
        with filesystem.open_read("data/input/records.csv") as stream:
            assert stream.read() == b"id,value\n1,test\n"

    def test_open_read_raises_file_not_found_for_missing_file(
        self,
        tmp_path: Path,
    ):
        # Arrange
        filesystem = LocalFileSystem(path_validator=PathValidator(base_path=tmp_path))

        # Act / Assert
        with pytest.raises(FileSystemError):
            filesystem.open_read("missing.csv")

    def test_open_read_rejects_path_outside_permitted_base(
        self,
        tmp_path: Path,
    ):
        # Arrange
        base_path = tmp_path / "permitted"
        outside_dir = tmp_path / "outside"

        base_path.mkdir()
        outside_dir.mkdir()

        outside_file = outside_dir / "secret.csv"
        outside_file.write_bytes(b"restricted,data\n")

        filesystem = LocalFileSystem(path_validator=PathValidator(base_path=base_path))

        # Act / Assert
        with pytest.raises(PathValidationError):
            filesystem.open_read(str(outside_file))


class TestLocalFileSystemOpenWrite:
    def test_open_write_creates_and_writes_new_file(self, tmp_path: Path):
        validator = PathValidator(base_path=tmp_path)
        storage = LocalFileSystem(path_validator=validator)
        content = b"ETLRelay test data"

        with storage.open_write("output.bin") as stream:
            assert stream.mode == "wb"
            stream.write(content)

        output_path = tmp_path / "output.bin"

        assert output_path.is_file()
        assert output_path.read_bytes() == content

    def test_open_write_overwrites_existing_file(self, tmp_path: Path):
        output_path = tmp_path / "output.bin"
        output_path.write_bytes(b"Original content")

        validator = PathValidator(base_path=tmp_path)
        storage = LocalFileSystem(path_validator=validator)

        with storage.open_write("output.bin") as stream:
            stream.write(b"Replacement")

        assert output_path.read_bytes() == b"Replacement"

    def test_open_write_rejects_path_outside_base(self, tmp_path: Path):
        base_path = tmp_path / "base"
        outside_path = tmp_path / "outside.bin"
        base_path.mkdir()

        validator = PathValidator(base_path=base_path)
        storage = LocalFileSystem(path_validator=validator)

        with pytest.raises(PathValidationError):
            storage.open_write(str(outside_path))

        assert not outside_path.exists()

    def test_open_write_raises_error_when_parent_directory_does_not_exist(
        self,
        tmp_path: Path,
    ):
        validator = PathValidator(base_path=tmp_path)
        storage = LocalFileSystem(path_validator=validator)

        with pytest.raises(FileNotFoundError):
            storage.open_write("missing/output.bin")

    def test_open_read_raises_filesystem_error_if_file_disappears_before_open(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        file_path = tmp_path / "input.bin"
        file_path.write_bytes(b"content")

        filesystem = LocalFileSystem(path_validator=PathValidator(base_path=tmp_path))

        def file_disappeared(
            _path: Path,
            *_args: Any,
            **_kwargs: Any,
        ) -> BinaryIO:
            raise FileNotFoundError("File disappeared before opening")

        monkeypatch.setattr(Path, "open", file_disappeared)

        with pytest.raises(FileSystemError):
            filesystem.open_read("input.bin")


class TestLocalFileSystemErrorPropagation:
    @pytest.mark.parametrize("operation", ["read", "write"])
    def test_open_propagates_permission_errors(
        self,
        operation: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        file_path = tmp_path / "protected.bin"
        file_path.write_bytes(b"content")

        filesystem = LocalFileSystem(path_validator=PathValidator(base_path=tmp_path))

        def permission_denied(
            _path: Path,
            *_args: Any,
            **_kwargs: Any,
        ) -> BinaryIO:
            raise PermissionError("Permission denied")

        monkeypatch.setattr(Path, "open", permission_denied)

        if operation == "read":
            open_resource = filesystem.open_read
        else:
            open_resource = filesystem.open_write

        with pytest.raises(PermissionError, match="Permission denied"):
            open_resource("protected.bin")

    @pytest.mark.parametrize("operation", ["read", "write"])
    @pytest.mark.parametrize("error_type", [PermissionError, OSError])
    def test_open_propagates_filesystem_errors(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        operation: str,
        error_type: type[OSError],
    ) -> None:
        file_path = tmp_path / "protected.bin"
        file_path.write_bytes(b"content")

        filesystem = LocalFileSystem(path_validator=PathValidator(base_path=tmp_path))

        def fail_open(
            _path: Path,
            *_args: Any,
            **_kwargs: Any,
        ) -> BinaryIO:
            raise error_type("Filesystem operation failed")

        monkeypatch.setattr(Path, "open", fail_open)

        open_resource = filesystem.open_read if operation == "read" else filesystem.open_write

        with pytest.raises(error_type, match="Filesystem operation failed"):
            open_resource("protected.bin")


class TestLocalFileSystemContainment:
    @pytest.mark.parametrize("operation", ["read", "write"])
    def test_rejects_relative_path_traversal(
        self,
        tmp_path: Path,
        operation: str,
    ) -> None:
        base_path = tmp_path / "base"
        base_path.mkdir()

        outside_path = tmp_path / "outside.bin"
        outside_path.write_bytes(b"original")

        filesystem = LocalFileSystem(PathValidator(base_path))
        open_resource = filesystem.open_read if operation == "read" else filesystem.open_write

        with pytest.raises(PathValidationError):
            open_resource("../outside.bin")

        assert outside_path.read_bytes() == b"original"

    @pytest.mark.parametrize("operation", ["read", "write"])
    def test_rejects_symlink_to_file_outside_base(
        self,
        tmp_path: Path,
        operation: str,
    ) -> None:
        base_path = tmp_path / "base"
        base_path.mkdir()

        outside_path = tmp_path / "outside.bin"
        outside_path.write_bytes(b"original")

        symlink = base_path / "link.bin"
        symlink.symlink_to(outside_path)

        filesystem = LocalFileSystem(PathValidator(base_path))
        open_resource = filesystem.open_read if operation == "read" else filesystem.open_write

        with pytest.raises(PathValidationError):
            open_resource("link.bin")

        assert outside_path.read_bytes() == b"original"

    @pytest.mark.parametrize("operation", ["read", "write"])
    def test_rejects_symlinked_parent_outside_base(
        self,
        tmp_path: Path,
        operation: str,
    ) -> None:
        base_path = tmp_path / "base"
        outside_dir = tmp_path / "outside"

        base_path.mkdir()
        outside_dir.mkdir()

        outside_path = outside_dir / "file.bin"
        outside_path.write_bytes(b"original")

        symlink = base_path / "linked"
        symlink.symlink_to(outside_dir, target_is_directory=True)

        filesystem = LocalFileSystem(PathValidator(base_path))
        open_resource = filesystem.open_read if operation == "read" else filesystem.open_write

        with pytest.raises(PathValidationError):
            open_resource("linked/file.bin")

        assert outside_path.read_bytes() == b"original"

    def test_open_write_rejects_symlink_to_nonexistent_path_outside_base(
        self,
        tmp_path: Path,
    ) -> None:
        base_path = tmp_path / "base"
        base_path.mkdir()

        outside_path = tmp_path / "new.bin"
        symlink = base_path / "link.bin"
        symlink.symlink_to(outside_path)

        filesystem = LocalFileSystem(PathValidator(base_path))

        with pytest.raises(PathValidationError):
            filesystem.open_write("link.bin")

        assert not outside_path.exists()
        assert symlink.is_symlink()

    def test_open_write_allows_symlink_to_file_inside_base(
        self,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / "target.bin"
        target.write_bytes(b"original")

        symlink = tmp_path / "link.bin"
        symlink.symlink_to(target)

        filesystem = LocalFileSystem(PathValidator(tmp_path))

        with filesystem.open_write("link.bin") as stream:
            stream.write(b"replacement")

        assert target.read_bytes() == b"replacement"
        assert symlink.is_symlink()

    @pytest.mark.parametrize("operation", ["read", "write"])
    def test_open_propagates_error_for_directory_path(
        self,
        tmp_path: Path,
        operation: str,
    ) -> None:
        directory = tmp_path / "directory"
        directory.mkdir()

        filesystem = LocalFileSystem(PathValidator(tmp_path))
        open_resource = filesystem.open_read if operation == "read" else filesystem.open_write

        with pytest.raises(OSError):
            open_resource("directory")

        assert directory.is_dir()
