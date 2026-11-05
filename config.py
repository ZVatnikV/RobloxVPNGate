from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = ROOT / "settings.json"
DEFAULT_PATH = ROOT / "settings.default.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_settings() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        shutil.copyfile(DEFAULT_PATH, SETTINGS_PATH)
    data = _load_json(DEFAULT_PATH)
    user = _load_json(SETTINGS_PATH)
    data.update(user)
    return data


def save_settings(data: dict[str, Any]) -> None:
    base = _load_json(DEFAULT_PATH)
    base.update(data)
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)