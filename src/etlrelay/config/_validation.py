"""Private helpers for validating ETLRelay configuration values.

This module provides reusable primitives for validating configuration structure,
including mapping types, supported and required keys, and non-empty string
values. Helpers return validation errors rather than raising exceptions, allowing
callers to aggregate errors before proceeding with configuration construction.
"""

from collections.abc import Mapping
from typing import cast


def as_mapping(
    config: object,
    path: str,
) -> tuple[Mapping[str, object] | None, list[str]]:
    """Validate that a configuration value is a mapping with string keys.

    Args:
        config: Configuration value to validate.
        path: Configuration path used to identify validation errors.

    Returns:
        A tuple containing:
        - The configuration cast to ``Mapping[str, object]`` if the value is
          a mapping, or ``None`` otherwise.
        - A list of validation errors. The list is empty when the value is a
          mapping with only string keys. A non-mapping value produces one
          error, while a mapping may produce one error for each non-string key.

    Note:
        When the value is a mapping with non-string keys, the mapping is still
        returned alongside the errors. Callers are responsible for checking
        the errors before relying on the mapping's validity.
    """
    if not isinstance(config, Mapping):
        return None, [f"{path} must be a mapping."]

    errors = [
        f"{path} contains a non-string key: {key!r}." for key in config if not isinstance(key, str)
    ]

    return cast(Mapping[str, object], config), errors


def validate_keys(
    config: Mapping[str, object],
    path: str,
    *,
    allowed: tuple[str, ...],
    required: tuple[str, ...],
) -> list[str]:
    """Validate the supported and required keys of a configuration mapping.

    Args:
        config: Configuration mapping whose keys are to be validated.
        path: Configuration path used as the prefix for validation errors.
        allowed: Tuple of permitted keys. Keys outside this set are reported
            as unsupported fields.
        required: Tuple of keys that must be present in the mapping.

    Returns:
        A list of validation errors. Each unsupported key and each missing
        required key produces a separate error. The list is empty when all
        keys are supported and all required keys are present.

    Note:
        This function validates key names and presence only. It does not
        validate the values associated with individual keys.
    """
    errors = [
        f"{path}.{key} is not a supported field."
        for key in config
        if isinstance(key, str) and key not in allowed
    ]

    errors.extend(f"{path}.{key} is required." for key in required if key not in config)

    return errors


def non_empty_string_error(
    value: object,
    path: str,
) -> str | None:
    """Validate that a configuration value is a non-empty string.

    Args:
        value: Value to validate.
        path: Configuration path used to identify the value in an error
            message.

    Returns:
        An error message if ``value`` is not a string or contains only
        whitespace; otherwise, ``None``.
    """
    if not isinstance(value, str) or not value.strip():
        return f"{path} must be a non-empty string."

    return None
