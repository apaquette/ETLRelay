"""Load and validate ETLRelay pipeline configurations.

This module provides a loader that reads configuration documents through a
filesystem abstraction, parses them using a key-value reader, and validates
the resulting configuration before returning it.
"""

from collections.abc import Mapping
from typing import Any

from etlrelay.config.validator import ConfigValidator
from etlrelay.core.reader import KeyValueReader
from etlrelay.storage.filesystem import FileSystem


class ConfigLoader:
    """Read, parse, and validate a pipeline configuration document.

    The loader coordinates filesystem access, document parsing, and
    configuration validation. It delegates these responsibilities to injected
    dependencies rather than implementing filesystem operations, parsing, or
    validation itself.
    """

    def __init__(
        self,
        filesystem: FileSystem,
        reader: KeyValueReader,
        validator: ConfigValidator,
    ) -> None:
        """Initialize the loader with its I/O and validation dependencies.

        Args:
            filesystem: Filesystem abstraction used to open the configuration
                document for reading.
            reader: Reader that parses the document stream into a configuration
                object.
            validator: Validator that checks the parsed configuration.
        """
        self._filesystem = filesystem
        self._reader = reader
        self._validator = validator

    def load(self, path: str) -> Mapping[str, Any]:
        """Read, parse, validate, and return a pipeline configuration.

        The document is opened through the configured filesystem, parsed by
        the configured reader, and validated before being returned. If reading
        or parsing fails, validation is not performed.

        Args:
            path: Path or resource identifier of the configuration document,
                interpreted by the configured filesystem.

        Returns:
            The parsed configuration mapping after successful validation.

        Raises:
            OSError: If an underlying filesystem or I/O operation raises this
                exception.
            Exception: Any parsing or validation exception raised by the
                configured reader or validator may propagate to the caller.
        """
        with self._filesystem.open_read(path) as stream:
            config = self._reader.read(stream)

        self._validator.validate(config)
        return config
