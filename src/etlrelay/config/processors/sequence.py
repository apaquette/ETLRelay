"""Validation for ordered processor configuration sequences."""

from etlrelay.config.component_validator import ComponentConfigValidator


class ProcessorSequenceConfigValidator:
    """Validate a sequence of processor configurations in order."""

    def __init__(
        self,
        processor_validator: ComponentConfigValidator,
    ) -> None:
        """Initialize the sequence validator with a processor dispatcher."""
        self._processor_validator = processor_validator

    def validate(self, config: object, path: str) -> list[str]:
        """Validate each processor configuration and aggregate errors.

        An empty list is valid. Each processor is validated independently,
        using an indexed path such as ``processors[0]``. Errors from one
        processor do not prevent validation of subsequent processors.
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
