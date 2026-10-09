"""Utilities for validating filesystem paths.

This module provides path validation to prevent paths from escaping a
configured base directory. Paths are resolved before validation so that
relative path traversal and symlink-based escapes are evaluated against
their resolved filesystem location.

Validated paths must exist and resolve to a location within the configured
base directory. When no base directory is provided, the current working
directory is used.
"""

from pathlib import Path


class PathValidator:
    """Validate filesystem paths against a trusted base directory.

    PathValidator resolves both the configured base directory and candidate
    paths before checking whether the candidate remains within the permitted
    directory. This prevents path traversal and symlink-based paths from
    escaping the configured boundary.

    Args:
        base_path: The directory that candidate paths must remain within.
            If None, the current working directory is used.

    Raises:
        PathValidationError: Raised by validate() when a candidate path is
            outside the base directory or does not exist.
    """

    def __init__(self, base_path: Path | None = None):
        self.base_path = (Path.cwd() if base_path is None else base_path).resolve()

    def validate(self, path: Path | str) -> Path:
        """Validate and resolve a filesystem path.

        The candidate path is resolved relative to the configured base
        directory. The resolved path must remain within the base directory
        and must exist on the filesystem.

        Args:
            path: The filesystem path to validate. May be a Path object or
                a string. Relative paths are resolved relative to the
                configured base directory.

        Returns:
            The resolved Path for the validated filesystem location.

        Raises:
            PathValidationError: If the resolved path is outside the
                configured base directory or does not exist.
        """
        path = Path(path)  # Convert to Path object if it's a string
        resolved_path = (self.base_path / path).resolve()

        if not resolved_path.is_relative_to(self.base_path):
            raise PathValidationError(f"Path {path} is outside the base directory")

        return resolved_path


class PathValidationError(Exception):
    """Raised when a filesystem path fails validation."""
