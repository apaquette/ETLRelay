"""Read safe, single-document YAML mappings from binary streams.

The reader uses PyYAML's safe loader and rejects duplicate mapping keys,
including duplicates exposed after YAML merge keys are flattened. It requires
the document root to be a mapping with string keys but leaves application-
specific schema validation to the configuration validator.
"""

from collections.abc import Mapping
from typing import Any, BinaryIO, cast

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode


class YamlDocumentError(ValueError):
    """Reject a YAML document that violates the root mapping contract.

    Syntax and duplicate-key errors remain ``yaml.YAMLError`` instances.
    This ValueError subclass distinguishes expected document-shape failures
    from unrelated programming errors without changing existing ValueError
    handling by library callers.
    """


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safely load YAML while rejecting duplicate mapping keys.

    This loader retains the safe-construction behavior of ``yaml.SafeLoader``
    and rejects duplicate or unhashable mapping keys. Duplicate-key detection
    occurs after YAML merge keys have been flattened, so a key inherited
    through a merge and repeated explicitly is also rejected.
    """

    def construct_mapping(
        self,
        node: MappingNode,
        deep: bool = False,
    ) -> dict[Any, Any]:
        """Construct a mapping and reject unhashable or duplicate keys.

        YAML merge keys are flattened before entries are processed. Each key
        is constructed and checked for hashability and duplication before its
        corresponding value is added to the result.

        Args:
            node: YAML mapping node to construct.
            deep: PyYAML construction flag indicating whether nested objects
                should be constructed deeply.

        Returns:
            A dictionary containing the constructed mapping entries.

        Raises:
            ConstructorError: If a mapping key is unhashable or appears more
                than once in the flattened mapping.
        """
        self.flatten_mapping(node)

        mapping: dict[Any, Any] = {}

        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)

            try:
                hash(key)
            except TypeError as exc:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable key",
                    key_node.start_mark,
                ) from exc

            if key in mapping:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )

            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value

        return mapping


class YamlReader:
    """Read a YAML document whose root is a string-keyed mapping.

    This reader handles safe YAML parsing and enforces the root mapping
    contract. It does not validate application-specific schema rules or
    restrict the key types of nested mappings.
    """

    def read(self, stream: BinaryIO) -> Mapping[str, Any]:
        """Parse a single YAML document from a binary stream.

        The YAML root must be a mapping, and all root-level keys must be
        strings. Duplicate keys are rejected by the custom safe loader.
        The stream is not explicitly closed by this method.

        Args:
            stream: Binary stream containing the YAML document.

        Returns:
            The parsed root mapping, with string keys at the root. Nested
            mappings may contain keys of other types.

        Raises:
            YamlDocumentError: If the parsed document root is not a mapping or any
                root-level key is not a string.
            yaml.YAMLError: If parsing fails, the document contains duplicate
                or unhashable mapping keys, or the stream contains multiple
                YAML documents instead of a single document.
        """
        document = yaml.load(stream, Loader=_UniqueKeySafeLoader)

        if not isinstance(document, Mapping):
            raise YamlDocumentError("YAML document must have a mapping at the root")

        for key in document:
            if not isinstance(key, str):
                raise YamlDocumentError(f"YAML root mapping keys must be strings; found {key!r}")

        return cast(Mapping[str, Any], document)
