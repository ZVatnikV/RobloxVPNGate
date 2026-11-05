from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


def resource_root() -> Path:
    """Bundled read-only assets (PyInstaller _MEIPASS or source tree)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def data_root() -> Path:
    """Writable user data directory for settings.json."""
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("APPDATA", Path.home())) / "RobloxVPNGate"
        base.mkdir(parents=True, exist_ok=True)
        return base
    return Path(__file__).resolve().parent


ROOT = resource_root()
SETTINGS_PATH = data_root() / "settings.json"
DEFAULT_PATH = resource_root() / "settings.default.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_settings() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DEFAULT_PATH, SETTINGS_PATH)
    data = _load_json(DEFAULT_PATH)
    user = _load_json(SETTINGS_PATH)
    data.update(user)
    return data


def save_settings(data: dict[str, Any]) -> None:
    base = _load_json(DEFAULT_PATH)
    base.update(data)
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)