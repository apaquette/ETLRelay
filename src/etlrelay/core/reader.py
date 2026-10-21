"""Protocols for reading tabular data and mapping-shaped documents.

TabularReader produces ETLRelay batches. KeyValueReader produces one
mapping-shaped document. Neither protocol owns the supplied binary stream.
"""

from collections.abc import Iterable, Mapping
from typing import Any, BinaryIO, Protocol, runtime_checkable

from etlrelay.core import Batch


class ReaderError(Exception):
    """Represent a read or parsing failure normalized by a reader implementation."""


@runtime_checkable
class TabularReader(Protocol):
    """Define the interface for reading tabular data from a binary stream.

    Implementations parse format-specific input into ETLRelay batches,
    independently of the storage system providing the stream.
    """

    def read(self, stream: BinaryIO) -> Iterable[Batch]:
        """Read serialized tabular data as an iterable of batches.

        Args:
            stream: An open, readable binary stream containing serialized
                tabular data.

        Returns:
            An iterable of parsed batches. Parsing may occur lazily during
            iteration.

        Note:
            The caller owns the supplied stream and must keep it open while
            consuming the returned iterable. Implementations must not close
            the stream, including when parsing or iteration fails.

            Stream requirements, empty-input behavior, batch boundaries,
            and parsing errors are documented by each implementation.
            Some formats require a seekable stream.
        """
        ...


@runtime_checkable
class KeyValueReader(Protocol):
    """Define the interface for reading one mapping-shaped document.

    The result represents a document with string keys, potentially containing
    nested values. It is distinct from an iterable of row mappings and from
    the tabular batches produced by TabularReader.

    Implementations parse the document independently of the storage system
    providing the stream.
    """

    def read(self, stream: BinaryIO) -> Mapping[str, Any]:
        """Read a mapping-shaped document from a binary stream.

        Args:
            stream: An open, readable binary stream containing a serialized
                document.

        Returns:
            A mapping with string keys representing the parsed document.

        Note:
            The caller owns the supplied stream. Implementations must finish
            reading the document before returning and must not close the
            stream, including when parsing fails.

            Nested value types, empty-input behavior, format restrictions,
            and parsing errors are documented by each implementation.
            This protocol does not define an application configuration
            schema; configuration validation is a separate responsibility.
        """
        ...
