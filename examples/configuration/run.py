"""Load, validate, build, and execute an ETLRelay YAML pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from etlrelay.config.loader import ConfigLoader
from etlrelay.config.pipeline_builder import PipelineBuilder
from etlrelay.default_components import create_default_component_catalog
from etlrelay.readers.yaml import YamlReader
from etlrelay.security import PathValidator
from etlrelay.storage import LocalFileSystem


def parse_args() -> argparse.Namespace:
    """Parse the required configuration path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="YAML pipeline configuration path")
    return parser.parse_args()


def main() -> None:
    """Execute a validated YAML pipeline and release managed SQL engines."""
    args = parse_args()
    config_path = args.config.resolve(strict=True)

    # The config document is read through the standard filesystem abstraction.
    config_filesystem = LocalFileSystem(
        path_validator=PathValidator(base_path=config_path.parent),
    )
    catalog = create_default_component_catalog()
    loader = ConfigLoader(
        filesystem=config_filesystem,
        reader=YamlReader(),
        validator=catalog.config_validator,
    )
    validated_config = loader.load(config_path.name)

    builder = PipelineBuilder(
        source_registry=catalog.source_registry,
        sink_registry=catalog.sink_registry,
        processor_registry=catalog.processor_registry,
        sql_engine_factory=catalog.sql_engine_factory,
    )

    try:
        pipeline = builder.build(validated_config)
        pipeline.run()
    finally:
        builder.close()

    print(f"Pipeline completed: {config_path}")


if __name__ == "__main__":
    main()
