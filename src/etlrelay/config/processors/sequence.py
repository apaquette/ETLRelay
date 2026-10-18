"""Validation for ordered processor configuration sequences.

This module provides a validator that checks processor configurations in
sequence, delegates individual validation to a component configuration
validator, and aggregates validation errors across the sequence.
"""

from etlrelay.config.component_validator import ComponentConfigValidator


class ProcessorSequenceConfigValidator:
    """Validate a sequence of processor configurations in order.

    Each processor configuration is validated independently by the supplied
    validator. Validation errors are collected in sequence order, allowing
    callers to report multiple invalid processor configurations together.
    An empty sequence is considered valid.
    """

    def __init__(
        self,
        processor_validator: ComponentConfigValidator,
    ) -> None:
        """Initialize the sequence validator with a processor validator.

        Args:
            processor_validator: Validator that checks individual processor
                configurations and returns their validation errors.
        """
        self._processor_validator = processor_validator

    def validate(self, config: object, path: str) -> list[str]:
        """Validate processor configurations and aggregate validation errors.

        The configuration must be a list. Each item is validated using an
        indexed configuration path, such as ``processors[0]``. Validation
        continues through the entire list even when an earlier item is invalid.

        Args:
            config: Value expected to be a list of processor configurations.
            path: Configuration path used as the base for identifying
                validation errors.

        Returns:
            A list of validation error messages. If ``config`` is not a list,
            the result contains a single error identifying that requirement.
            Otherwise, the result contains the errors reported for each
            processor, in sequence order. An empty list is valid and produces
            no errors; an empty error list indicates that validation succeeded.
        """
        if not isinstance(config, list):
            return [f"{path} must be a list."]

        errors: list[str] = []

        for index, processor_config in enumerate(config):
            processor_path = f"{path}[{index}]"
            errors.extend(
                self._processor_validator.validate(
                    processor_config,
                    processor_path,
                )
            )

        return errors
