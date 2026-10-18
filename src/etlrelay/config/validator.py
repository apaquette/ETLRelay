"""Root validation for versioned ETLRelay pipeline configurations.

This module validates the top-level structure and supported version of a
pipeline configuration, then delegates validation of the source, processor
sequence, and sink sections to their respective validators.
"""

from etlrelay.config._validation import as_mapping
from etlrelay.config.component_validator import ComponentConfigValidator
from etlrelay.config.errors import ConfigurationError


class ConfigValidator:
    """Validate a complete versioned pipeline configuration.

    The validator enforces the root configuration schema, including the
    supported version and required top-level fields. It delegates validation
    of individual pipeline sections to the injected component validators and
    aggregates their errors with any root-level validation errors.

    Attributes:
        SUPPORTED_VERSION: The configuration schema version accepted by this
            validator.
    """

    SUPPORTED_VERSION = 1

    def __init__(
        self,
        source_validator: ComponentConfigValidator,
        processor_validator: ComponentConfigValidator,
        sink_validator: ComponentConfigValidator,
    ) -> None:
        """Initialize the validator with the component-family validators.

        Args:
            source_validator: Validator for the source configuration section.
            processor_validator: Validator for the ordered processor
                configuration sequence.
            sink_validator: Validator for the sink configuration section.
        """
        self._source_validator = source_validator
        self._processor_validator = processor_validator
        self._sink_validator = sink_validator

    def validate(self, config: object) -> None:
        """Validate the root schema and all present pipeline sections.

        The root value must be a mapping with string keys. The supported
        top-level fields are ``version``, ``source``, ``processors``, and
        ``sink``, and all four fields are required. The version must be the
        integer specified by ``SUPPORTED_VERSION``.

        After checking the root mapping, this method delegates validation of
        each present pipeline section and aggregates the reported errors.
        Root values that are not mappings, or mappings containing non-string
        keys, are rejected before section validation begins.

        Args:
            config: Configuration value to validate.

        Raises:
            ConfigurationError: If the root configuration is malformed,
                contains unsupported or missing fields, uses an unsupported
                version, or contains errors reported by a section validator.
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
