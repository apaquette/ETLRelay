"""Configuration validator for local filesystem storage."""

from etlrelay.config._validation import (
    as_mapping,
    non_empty_string_error,
    validate_keys,
)


class LocalFileStorageValidator:
    """Validate configuration for local filesystem storage."""

    def validate(self, config: object, path: str) -> list[str]:
        """Validate local storage settings and return any errors.

        The ``type`` field must be ``local``. ``base_path`` is optional and
        defaults to the current directory when it is omitted. The validator
        checks configuration shape only; it does not access the filesystem.
        """
        mapping, errors = as_mapping(config, path)
        if mapping is None:
            return errors

        errors.extend(
            validate_keys(
                mapping,
                path,
                allowed=("type", "base_path"),
                required=("type",),
            )
        )

        if "type" in mapping and mapping["type"] != "local":
            errors.append(f"{path}.type must be 'local'.")

        if "base_path" in mapping:
            error = non_empty_string_error(
                mapping["base_path"],
                f"{path}.base_path",
            )
            if error is not None:
                errors.append(error)

        return errors