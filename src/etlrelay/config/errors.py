"""Exceptions raised by ETLRelay configuration APIs."""


class ConfigurationError(Exception):
    """Raised when a configuration-related operation fails.

    This exception represents failures that prevent a configuration operation
    from completing successfully.
    """
