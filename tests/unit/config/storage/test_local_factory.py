"""Unit tests for the local filesystem configuration factory."""

from pathlib import Path
from unittest.mock import patch

from etlrelay.config.storage.local import LocalFileSystemConfigFactory


def test_build_uses_configured_base_path() -> None:
    config = {"type": "local", "base_path": "/var/tmp/etlrelay-data"}

    with (
        patch("etlrelay.config.storage.local.PathValidator") as path_validator,
        patch("etlrelay.config.storage.local.LocalFileSystem") as local_filesystem,
    ):
        result = LocalFileSystemConfigFactory().build(config)

    path_validator.assert_called_once_with(base_path=Path("/var/tmp/etlrelay-data"))
    local_filesystem.assert_called_once_with(path_validator=path_validator.return_value)
    assert result is local_filesystem.return_value


def test_build_defaults_base_path_to_current_directory() -> None:
    config = {"type": "local"}

    with (
        patch("etlrelay.config.storage.local.PathValidator") as path_validator,
        patch("etlrelay.config.storage.local.LocalFileSystem") as local_filesystem,
    ):
        result = LocalFileSystemConfigFactory().build(config)

    path_validator.assert_called_once_with(base_path=Path("."))
    local_filesystem.assert_called_once_with(path_validator=path_validator.return_value)
    assert result is local_filesystem.return_value
