"""Shared SQL validation functions."""

from collections import Counter
from collections.abc import Sequence
from typing import Any

from sqlalchemy.engine import Engine


def validate_engine(engine: Any) -> list[str]:
    """Validate a SQLAlchemy engine.

    Args:
        engine: Object to validate as a SQLAlchemy ``Engine``.

    Returns:
        An empty list when the engine is valid; otherwise, a list containing
        validation error messages.
    """
    if not isinstance(engine, Engine):
        return ["engine must be a SQLAlchemy Engine"]

    return []


def validate_unique_columns(column_names: Sequence[str]) -> None:
    """Ensure column names are unique.

    Used to validate SQL result column names and Arrow batch column names.

    Args:
        column_names: Sequence of column names to validate.

    Raises:
        ValueError: If one or more column names occur more than once.
            The exception identifies the duplicated names.
    """
    duplicates = sorted(name for name, count in Counter(column_names).items() if count > 1)

    if duplicates:
        raise ValueError(f"Duplicate column names detected: {duplicates}")
