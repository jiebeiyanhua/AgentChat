import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path("config/app_config.json")


def get_config_path() -> Path:
    return Path(os.getenv("APP_CONFIG_FILE", DEFAULT_CONFIG_PATH.as_posix()))


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    config_path = get_config_path()
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            "Create it from config/app_config.example.json or set APP_CONFIG_FILE."
        )

    with config_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Application config must be a JSON object.")
    return data


def _walk_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def get_config(path: str, default: Any = None) -> Any:
    try:
        return _walk_path(load_config(), path)
    except KeyError:
        return default


def require_config(path: str) -> Any:
    try:
        return _walk_path(load_config(), path)
    except KeyError as exc:
        raise ValueError(f"Missing required config: {path}") from exc


def get_str(path: str, default: str | None = None) -> str | None:
    value = get_config(path, default)
    if value is None:
        return None
    return str(value)


def require_str(path: str) -> str:
    value = require_config(path)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Missing required config: {path}")
    return str(value)


def get_int(path: str, default: int) -> int:
    value = get_config(path, default)
    return int(value)


def get_float(path: str, default: float) -> float:
    value = get_config(path, default)
    return float(value)


def get_bool(path: str, default: bool = False) -> bool:
    value = get_config(path, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def reload_config() -> dict[str, Any]:
    load_config.cache_clear()
    return load_config()


def save_config(data: dict[str, Any]) -> Path:
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
    reload_config()
    return config_path
