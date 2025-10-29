from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

_FIRSTTRY_DIR = Path(os.path.expanduser("~")) / ".firsttry"
_LAST_RUN_PATH = _FIRSTTRY_DIR / "last_run.json"


def _ensure_dir() -> None:
    _FIRSTTRY_DIR.mkdir(parents=True, exist_ok=True)


def save_last_run(summary: Dict[str, Any]) -> None:
    _ensure_dir()
    tmp = _LAST_RUN_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    tmp.replace(_LAST_RUN_PATH)


def load_last_run() -> Optional[Dict[str, Any]]:
    if not _LAST_RUN_PATH.exists():
        return None
    try:
        with _LAST_RUN_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
