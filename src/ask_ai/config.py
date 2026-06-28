from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR_ENV = "ASK_CONFIG_DIR"
CONFIG_FILE_NAME = "config.json"


def config_dir() -> Path:
    configured = os.environ.get(CONFIG_DIR_ENV)
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".config" / "ask-ai"


def config_path() -> Path:
    return config_dir() / CONFIG_FILE_NAME


def load_api_key() -> str | None:
    path = config_path()
    if not path.exists():
        return None

    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict):
        return None

    api_key = data.get("api_key")
    if not isinstance(api_key, str):
        return None

    api_key = api_key.strip()
    return api_key or None


def save_api_key(api_key: str) -> Path:
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("API key cannot be empty.")

    path = config_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"api_key": api_key}, indent=2) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


def delete_api_key() -> bool:
    path = config_path()
    if not path.exists():
        return False
    path.unlink()
    return True
