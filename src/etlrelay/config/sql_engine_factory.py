"""Create and manage SQLAlchemy engines for configured SQL components.

This module defines the interface used by SQL component factories to obtain
engines and implements environment-variable preflight, engine caching, and
resource cleanup. Connection URLs are resolved before engine creation and are
not included in errors raised by the factory.
"""

import os
from collections.abc import Callable, Mapping
from typing import Protocol

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

EnvironmentLookup = Callable[[str], str | None]
"""Callable that retrieves an environment variable by name."""

EngineCreator = Callable[[str], Engine]
"""Callable that creates a SQLAlchemy engine from a connection URL."""


class SqlEngineProvider(Protocol):
    """Define the minimal interface required by SQL component factories.

    Implementations provide SQLAlchemy engines associated with connection
    references that have already passed environment-variable preflight.
    """

    def create(self, variable_name: str) -> Engine:
        """Return the engine associated with a preflighted variable name.

        Args:
            variable_name: Name of the environment variable whose resolved
                connection URL identifies the engine.

        Returns:
            The SQLAlchemy engine associated with the specified variable name.

        Raises:
            SqlEngineFactoryError: If the implementation cannot provide an
                engine for the requested variable name.
        """
        ...


class SqlEngineFactoryError(ValueError):
    """Raised when SQL environment preflight or engine management fails.

    This exception represents failures such as missing connection
    configuration, engine creation errors, and engine disposal errors.
    Error messages are designed to avoid exposing connection URLs or
    credentials.
    """


class SqlEngineFactory:
    """Resolve SQL connection URLs and manage SQLAlchemy engine lifecycles.

    Environment-variable references must pass preflight before engines can be
    created. Successful preflight stores resolved connection URLs without
    creating engines. Engines are created on demand and cached by environment
    variable name.

    The factory owns the engines it creates and disposes of them when
    ``close()`` is called. Closing also discards resolved connection URLs.
    Environment lookup and engine creation can be injected for testing.
    """

    def __init__(
        self,
        getenv: EnvironmentLookup | None = None,
        engine_creator: EngineCreator | None = None,
    ) -> None:
        """Initialize the factory with optional environment and engine adapters.

        Args:
            getenv: Callable used to retrieve environment variables. Defaults
                to ``os.environ.get`` when omitted.
            engine_creator: Callable used to create SQLAlchemy engines from
                resolved connection URLs. Defaults to ``sqlalchemy.create_engine``
                when omitted.
        """
        self._getenv: EnvironmentLookup = getenv if getenv is not None else os.environ.get
        self._engine_creator: EngineCreator = (
            engine_creator if engine_creator is not None else create_engine
        )
        self._resolved_urls: dict[str, str] | None = None
        self._engines: dict[str, Engine] = {}

    def preflight(self, references: Mapping[str, str]) -> None:
        """Resolve and validate all referenced connection environment variables.

        The mapping associates configuration paths with environment-variable
        names. Each unique variable is read once, and missing or empty values
        are aggregated into a single error. No engines are created during
        preflight.

        A successful preflight replaces any previous resolved URL set. A
        failed preflight leaves resolved URLs unavailable for engine creation.
        Preflight cannot be repeated while the factory has active engines.

        Args:
            references: Mapping from configuration paths to environment-variable
                names that provide SQL connection URLs.

        Raises:
            SqlEngineFactoryError: If engines are already active, a reference
                has an invalid path or variable name, or one or more referenced
                environment variables are missing or empty.

        Note:
            Exceptions raised by the environment lookup callable are treated
            as missing environment-variable values. Error messages do not
            include resolved URLs or environment lookup exception details.
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
        """Create or retrieve the engine for a successfully preflighted variable.

        Engines are created on demand and cached by environment-variable name.
        Subsequent requests for the same name return the cached engine rather
        than creating another instance.

        Args:
            variable_name: Name of the environment variable whose connection
                URL was resolved during successful preflight.

        Returns:
            The cached SQLAlchemy engine for the variable, or a newly created
            engine that is stored for subsequent requests.

        Raises:
            SqlEngineFactoryError: If successful preflight has not occurred,
                the variable was not included in preflight, or engine creation
                fails. Engine creation errors identify the exception type
                without exposing the underlying exception message or connection
                URL.
        """
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
        """Dispose of owned engines and discard resolved connection URLs.

        Engine disposal is attempted in reverse creation order. The factory
        clears its engine cache and resolved URLs before disposal, and continues
        disposing remaining engines if one fails. Calling this method more than
        once is safe.

        Raises:
            SqlEngineFactoryError: If one or more engines cannot be disposed.
                The error does not include underlying disposal exception details.
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
