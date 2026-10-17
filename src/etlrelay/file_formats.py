"""Registry for tabular file-format reader and writer factories."""

from collections.abc import Callable, Mapping
from typing import TypeVar

ReaderT = TypeVar("ReaderT")
WriterT = TypeVar("WriterT")


class TabularFileFormatRegistry[ReaderT, WriterT]:
    """Register and construct readers and writers for tabular formats.

    Reading and writing capabilities are registered independently. A format
    may support reading, writing, both, or neither.

    The registry copies its input mappings during initialization and preserves
    their insertion order. Factory callables are invoked only when the
    corresponding creation method is called.
    """

    def __init__(
        self,
        readers: Mapping[str, Callable[[], ReaderT]],
        writers: Mapping[str, Callable[[], WriterT]],
    ) -> None:
        """Initialize the registry with reader and writer factories.

        Args:
            readers: Mapping of format names to reader factories.
            writers: Mapping of format names to writer factories.
        """
        self._readers = dict(readers)
        self._writers = dict(writers)

    def supports_reading(self, name: str) -> bool:
        """Return whether a reader is registered for the given format.

        Args:
            name: Format name to check.
        """
        return name in self._readers

    def supports_writing(self, name: str) -> bool:
        """Return whether a writer is registered for the given format.

        Args:
            name: Format name to check.
        """
        return name in self._writers

    def readable_formats(self) -> tuple[str, ...]:
        """Return readable format names in registration order."""
        return tuple(self._readers)

    def writable_formats(self) -> tuple[str, ...]:
        """Return writable format names in registration order."""
        return tuple(self._writers)

    def create_reader(self, name: str) -> ReaderT:
        """Construct a reader for a registered format.

        Args:
            name: Format name whose reader should be constructed.

        Returns:
            A new reader created by the registered factory.

        Raises:
            KeyError: If no reader is registered for the format.
        """
        try:
            factory = self._readers[name]
        except KeyError:
            raise KeyError(f"No reader registered for format: {name}") from None

        return factory()

    def create_writer(self, name: str) -> WriterT:
        """Construct a writer for a registered format.

        Args:
            name: Format name whose writer should be constructed.

        Returns:
            A new writer created by the registered factory.

        Raises:
            KeyError: If no writer is registered for the format.
        """
        try:
            factory = self._writers[name]
        except KeyError:
            raise KeyError(f"No writer registered for format: {name}") from None

        return factory()
