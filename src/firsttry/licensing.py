from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def get_global_license_path() -> Path:
    # POSIX: respect XDG config home
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "firsttry" / "license.json"

    # Windows
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "firsttry" / "license.json"

    # default
    return Path.home() / ".config" / "firsttry" / "license.json"


def save_license(key: str) -> None:
    path = get_global_license_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"license_key": key.strip()}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_license() -> dict[str, Any] | None:
    path = get_global_license_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
