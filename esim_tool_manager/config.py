from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


def config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "esim-tool-manager"


def config_path() -> Path:
    return config_dir() / "config.json"


def _empty_config() -> dict[str, dict[str, str]]:
    return {"paths": {}, "minimum_versions": {}}


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return _empty_config()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Could not read {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Configuration in {path} must be a JSON object.")

    config = _empty_config()
    for section in config:
        values = data.get(section, {})
        if not isinstance(values, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in values.items()
        ):
            raise ConfigError(
                f"The {section!r} setting in {path} must map tool names to text."
            )
        config[section] = values
    return config


def save_config(config: dict[str, Any]) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path
