"""Validate path containment within a configured base directory.

Relative paths are resolved against the configured base directory. Absolute
paths are accepted only when their resolved locations remain within that
directory. Path resolution normalizes dot segments and resolves symlinks
before containment is checked.

Validation does not require the target to exist or verify that the process
has permission to access it. Existence and access errors are determined by
the subsequent filesystem operation.

This is a path-containment check, not an operating-system sandbox. Filesystem
state may change between validation and a subsequent operation, so validation
does not eliminate time-of-check/time-of-use (TOCTOU) races.
"""

from pathlib import Path


class PathValidator:
    """Validate filesystem paths against a trusted base directory.

    PathValidator resolves both the configured base directory and candidate
    paths before checking whether the candidate remains within the permitted
    directory. This rejects path traversal and symlink-based escapes at
    validation time.

    Validation does not require the target to exist or guarantee that
    filesystem state remains unchanged after validation.

    Args:
        base_path: The directory that candidate paths must remain within.
            If None, the current working directory is used.

    Raises:
        PathValidationError: Raised by validate() when a candidate path
            resolves outside the permitted base directory.
    """

    def __init__(self, base_path: Path | None = None):
        self.base_path = (Path.cwd() if base_path is None else base_path).resolve()

    def validate(self, path: Path | str) -> Path:
        """Resolve a path and ensure it remains within the permitted base directory.

        Args:
            path: Relative or absolute path to validate.

        Returns:
            The resolved path, which does not need to exist yet.

        Raises:
            PathValidationError: If the resolved path is outside the permitted
                base directory.

        Note:
            This method checks path containment, not existence or access permissions.
            A subsequent filesystem operation can still fail, and filesystem state
            can change after validation.
        """
        path = Path(path)  # Convert to Path object if it's a string
        resolved_path = (self.base_path / path).resolve()

        if not resolved_path.is_relative_to(self.base_path):
            raise PathValidationError(f"Path {path} is outside the base directory")

        return resolved_path


class PathValidationError(Exception):
    """Raised when a filesystem path fails validation."""
