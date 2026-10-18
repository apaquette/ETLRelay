"""Create and manage SQLAlchemy engines for configured SQL components."""

import os
from collections.abc import Callable, Mapping
from typing import Protocol

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

EnvironmentLookup = Callable[[str], str | None]
EngineCreator = Callable[[str], Engine]


class SqlEngineProvider(Protocol):
    """Minimal interface required by SQL component factories."""

    def create(self, variable_name: str) -> Engine:
        """Return the engine associated with a preflighted variable name."""
        ...


class SqlEngineFactoryError(ValueError):
    """Raised when SQL environment preflight or engine management fails."""


class SqlEngineFactory:
    """Resolve SQL connection URLs and manage engines created from them.

    Preflight every component's environment-variable reference before calling
    ``create``. Engine instances are cached by variable name and disposed by
    ``close``. Resolved URLs are never included in errors.
    """

    def __init__(
        self,
        getenv: EnvironmentLookup | None = None,
        engine_creator: EngineCreator | None = None,
    ) -> None:
        self._getenv: EnvironmentLookup = getenv if getenv is not None else os.environ.get
        self._engine_creator: EngineCreator = (
            engine_creator if engine_creator is not None else create_engine
        )
        self._resolved_urls: dict[str, str] | None = None
        self._engines: dict[str, Engine] = {}

    def preflight(self, references: Mapping[str, str]) -> None:
        """Resolve all referenced variables without creating any engines.

        ``references`` maps configuration paths to environment-variable names.
        Missing or empty values are aggregated so callers can fix all issues
        at once. Each unique environment-variable name is read only once.
        """
        if self._engines:
            raise SqlEngineFactoryError(
                "Cannot rerun SQL preflight while engines are active; close the factory first."
            )

        # Invalidate any earlier result before attempting a new preflight.
        self._resolved_urls = None
        values: dict[str, str | None] = {}
        errors: list[str] = []

        for path, variable_name in references.items():
            if not isinstance(path, str) or not path.strip():
                errors.append("SQL environment reference has an invalid configuration path.")
                continue
            if not isinstance(variable_name, str) or not variable_name.strip():
                errors.append(f"{path} must reference a non-empty environment-variable name.")
                continue

            if variable_name not in values:
                try:
                    value = self._getenv(variable_name)
                except Exception:
                    # Avoid exposing any environment adapter's exception text.
                    value = None
                values[variable_name] = value if isinstance(value, str) and value.strip() else None

            if values[variable_name] is None:
                errors.append(
                    f"{path} references missing or empty environment variable '{variable_name}'."
                )

        if errors:
            raise SqlEngineFactoryError("SQL engine preflight failed:\n - " + "\n - ".join(errors))

        self._resolved_urls = {name: value for name, value in values.items() if value is not None}

    def create(self, variable_name: str) -> Engine:
        """Create or reuse the engine for a variable resolved during preflight."""
        if self._resolved_urls is None:
            raise SqlEngineFactoryError("SQL engine preflight must succeed before engine creation.")
        if variable_name not in self._resolved_urls:
            raise SqlEngineFactoryError(
                f"Environment variable '{variable_name}' was not included in "
                "successful SQL preflight."
            )

        if variable_name in self._engines:
            return self._engines[variable_name]

        try:
            engine = self._engine_creator(self._resolved_urls[variable_name])
        except Exception as exc:
            # The driver exception may contain the connection URL or credentials.
            raise SqlEngineFactoryError(
                f"Could not create SQLAlchemy engine for environment variable "
                f"'{variable_name}' ({type(exc).__name__})."
            ) from None

        self._engines[variable_name] = engine
        return engine

    def close(self) -> None:
        """Dispose owned engines once and discard resolved URLs.

        Attempts disposal for every engine. A generic error is raised if any
        disposal fails, without forwarding database-driver exception text.
        Calling close more than once is safe.
        """
        engines = tuple(reversed(tuple(self._engines.values())))
        self._engines.clear()
        self._resolved_urls = None

        failed = False
        for engine in engines:
            try:
                engine.dispose()
            except Exception:
                failed = True

        if failed:
            raise SqlEngineFactoryError(
                "One or more SQLAlchemy engines could not be disposed."
            ) from None
