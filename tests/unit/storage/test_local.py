from pathlib import Path

import pytest

from flowforge.security.path import PathValidationError, PathValidator
from flowforge.storage.filesystem import FileSystem, FileSystemError
from flowforge.storage.local import LocalFileSystem


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

        filesystem = LocalFileSystem(
            path_validator=PathValidator(base_path=tmp_path)
        )

        # Act / Assert
        with filesystem.open_read("input.csv") as stream:
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

        filesystem = LocalFileSystem(
            path_validator=PathValidator(base_path=tmp_path)
        )

        # Act / Assert
        with filesystem.open_read("data/input/records.csv") as stream:
            assert stream.read() == b"id,value\n1,test\n"

    def test_open_read_raises_file_not_found_for_missing_file(
        self,
        tmp_path: Path,
    ):
        # Arrange
        filesystem = LocalFileSystem(
            path_validator=PathValidator(base_path=tmp_path)
        )

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

        filesystem = LocalFileSystem(
            path_validator=PathValidator(base_path=base_path)
        )

        # Act / Assert
        with pytest.raises(PathValidationError):
            filesystem.open_read(str(outside_file))

class TestLocalFileSystemOpenWrite:
    def test_open_write_creates_and_writes_new_file(self, tmp_path: Path):
        validator = PathValidator(base_path=tmp_path)
        storage = LocalFileSystem(path_validator=validator)
        content = b"FlowForge test data"

        with storage.open_write("output.bin") as stream:
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