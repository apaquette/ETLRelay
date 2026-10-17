"""Private helpers for configuration validation."""

from collections.abc import Mapping
from typing import cast


def as_mapping(
    config: object,
    path: str,
) -> tuple[Mapping[str, object] | None, list[str]]:
    """Return a configuration mapping and errors for invalid mapping shape."""
    if not isinstance(config, Mapping):
        return None, [f"{path} must be a mapping."]

    errors = [
        f"{path} contains a non-string key: {key!r}."
        for key in config
        if not isinstance(key, str)
    ]

    return cast(Mapping[str, object], config), errors


def validate_keys(
    config: Mapping[str, object],
    path: str,
    *,
    allowed: tuple[str, ...],
    required: tuple[str, ...],
) -> list[str]:
    """Report unsupported keys and missing required fields."""
    errors = [
        f"{path}.{key} is not a supported field."
        for key in config
        if isinstance(key, str) and key not in allowed
    ]

    errors.extend(
        f"{path}.{key} is required."
        for key in required
        if key not in config
    )

    return errors


def non_empty_string_error(
    value: object,
    path: str,
) -> str | None:
    """Return an error when a value is not a non-empty string."""
    if not isinstance(value, str) or not value.strip():
        return f"{path} must be a non-empty string."

    return None