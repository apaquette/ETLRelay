"""Loading and validation of ETLRelay pipeline configurations."""

from collections.abc import Mapping
from typing import Any

from etlrelay.config.validator import ConfigValidator
from etlrelay.core.reader import KeyValueReader
from etlrelay.storage.filesystem import FileSystem


class ConfigLoader:
    """Read and validate a pipeline configuration document."""

    def __init__(
        self,
        filesystem: FileSystem,
        reader: KeyValueReader,
        validator: ConfigValidator,
    ) -> None:
        """Initialize the loader with its I/O and validation dependencies."""
        self._filesystem = filesystem
        self._reader = reader
        self._validator = validator

    def load(self, path: str) -> Mapping[str, Any]:
        """Read, validate, and return a pipeline configuration.

        Args:
            path: Path or resource identifier for the configuration document.

        Returns:
            The validated configuration mapping.

        Raises:
            ConfigurationError: If configuration validation fails.
            FileSystemError: If the requested resource does not exist.
            OSError: If another filesystem or I/O error occurs.
        """
        with self._filesystem.open_read(path) as stream:
            config = self._reader.read(stream)

        self._validator.validate(config)
        return config
