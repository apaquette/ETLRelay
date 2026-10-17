"""Root validation for versioned ETLRelay pipeline configurations."""

from etlrelay.config._validation import as_mapping
from etlrelay.config.component_validator import ComponentConfigValidator
from etlrelay.config.errors import ConfigurationError


class ConfigValidator:
    """Validate a complete versioned pipeline configuration."""

    SUPPORTED_VERSION = 1

    def __init__(
        self,
        source_validator: ComponentConfigValidator,
        processor_validator: ComponentConfigValidator,
        sink_validator: ComponentConfigValidator,
    ) -> None:
        """Initialize the validator with the component-family validators."""
        self._source_validator = source_validator
        self._processor_validator = processor_validator
        self._sink_validator = sink_validator

    def validate(self, config: object) -> None:
        """Validate the root schema and all present pipeline sections.

        Raises:
            ConfigurationError: If the configuration is malformed,
                contains unsupported fields, uses an unsupported version,
                or has errors reported by a component validator.
        """
        mapping, errors = as_mapping(config, "configuration")

        # Do not delegate a root object that cannot be safely interpreted.
        if mapping is None or errors:
            raise ConfigurationError(errors)

        allowed_fields = ("version", "source", "processors", "sink")

        for key in mapping:
            if key not in allowed_fields:
                errors.append(f"Unknown top-level configuration field: {key!r}.")

        for field in allowed_fields:
            if field not in mapping:
                errors.append(f"Required top-level field '{field}' is missing.")

        if "version" in mapping:
            version = mapping["version"]
            if type(version) is not int or version != self.SUPPORTED_VERSION:
                errors.append(f"version must be the integer {self.SUPPORTED_VERSION}.")

        if "source" in mapping:
            errors.extend(
                self._source_validator.validate(
                    mapping["source"],
                    "source",
                )
            )

        if "processors" in mapping:
            errors.extend(
                self._processor_validator.validate(
                    mapping["processors"],
                    "processors",
                )
            )

        if "sink" in mapping:
            errors.extend(
                self._sink_validator.validate(
                    mapping["sink"],
                    "sink",
                )
            )

        if errors:
            raise ConfigurationError(errors)
