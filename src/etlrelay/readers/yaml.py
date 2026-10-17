"""Read safe, single-document YAML mappings from binary streams."""

from collections.abc import Mapping
from typing import Any, BinaryIO, cast

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safely load YAML while rejecting duplicate mapping keys.

    Mapping keys are checked after YAML merge keys have been flattened.
    Consequently, a key inherited through a merge and repeated explicitly
    is also rejected.
    """

    def construct_mapping(
        self,
        node: MappingNode,
        deep: bool = False,
    ) -> dict[Any, Any]:
        """Construct a mapping, rejecting unhashable and duplicate keys.

        Raises:
            ConstructorError: If a key is unhashable or a key occurs more
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

    This reader handles YAML parsing and the mapping-shaped output contract.
    It does not validate an application's schema or the structure of nested
    mappings.
    """

    def read(self, stream: BinaryIO) -> Mapping[str, Any]:
        """Parse one YAML document from a binary stream.

        The stream remains open after this method returns or raises.

        Args:
            stream: A binary stream containing one YAML document, positioned
                at the beginning of the document.

        Returns:
            The parsed root mapping. Root-level keys are guaranteed to be
            strings. Nested mapping keys are not restricted to strings by
            this reader.

        Raises:
            ValueError: If the document root is not a mapping or if a
                root-level key is not a string.
            yaml.YAMLError: If the YAML is malformed, contains duplicate
                mapping keys, contains unhashable mapping keys, or contains
                multiple documents.
        """
        document = yaml.load(stream, Loader=_UniqueKeySafeLoader)

        if not isinstance(document, Mapping):
            raise ValueError("YAML document must have a mapping at the root")

        for key in document:
            if not isinstance(key, str):
                raise ValueError(f"YAML root mapping keys must be strings; found {key!r}")

        return cast(Mapping[str, Any], document)
