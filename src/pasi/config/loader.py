"""YAML configuration loaders (no domain validation beyond parse)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from pasi.config.settings import Settings, get_settings


def load_yaml_config(path: Path | str) -> dict[str, Any]:
    """Load a YAML file into a plain dictionary."""
    config_path = Path(path)
    if not config_path.is_absolute():
        settings = get_settings()
        config_path = settings.resolve(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at root of {config_path}")
    return data


def load_named_config(name: str, settings: Settings | None = None) -> dict[str, Any]:
    """Load `configs/{name}.yaml` (name without extension)."""
    settings = settings or get_settings()
    path = settings.resolve(settings.configs_dir / f"{name}.yaml")
    return load_yaml_config(path)
