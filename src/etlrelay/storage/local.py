"""Local filesystem implementation for ETLRelay.

This module provides binary read and write access to local filesystem
resources through the FileSystem interface. Paths are validated against
a permitted base directory before filesystem operations are performed.
"""

from typing import BinaryIO

from etlrelay.security.path import PathValidator
from etlrelay.storage.filesystem import FileSystemError


class LocalFileSystem:
    """Provide validated binary I/O for the local filesystem.

    LocalFileSystem uses PathValidator to enforce the permitted filesystem
    boundary before opening files. It returns binary streams so that
    format-specific readers and writers can operate independently of the
    underlying storage implementation.

    Args:
        path_validator: Validator used to ensure paths remain within the
            permitted base directory.
    """

    def __init__(self, path_validator: PathValidator):
        self._path_validator = path_validator

    def open_read(self, path: str) -> BinaryIO:
        """Open a validated local file for binary reading.

        The path is validated and must refer to an existing filesystem
        resource that can be opened for reading.

        Args:
            path: Path to the file, relative to the validator's base
                directory or an absolute path permitted by the validator.

        Returns:
            A readable binary stream. The caller is responsible for closing
            the stream, preferably by using a context manager.

        Raises:
            PathValidationError: If the path resolves outside the permitted
                base directory.
            FileSystemError: If the path does not exist.
            OSError: If the file cannot be opened or read.
        """
        validated_path = self._path_validator.validate(path)
        if not validated_path.exists():
            raise FileSystemError("Path does not exist")
        return validated_path.open("rb")

    def open_write(self, path: str) -> BinaryIO:
        """Open a validated local file for binary writing.

        The path is validated before the file is opened. If the destination
        does not exist, it is created. If it already exists, its contents
        are truncated. Parent directories are not created automatically.

        Args:
            path: Destination path, relative to the validator's base
                directory or an absolute path permitted by the validator.

        Returns:
            A writable binary stream. The caller is responsible for closing
            the stream, preferably by using a context manager.

        Raises:
            PathValidationError: If the path resolves outside the permitted
                base directory.
            OSError: If the destination cannot be opened for writing, such
                as when its parent directory does not exist or access is
                denied.
        """
        validated_path = self._path_validator.validate(path)
        return validated_path.open("wb")