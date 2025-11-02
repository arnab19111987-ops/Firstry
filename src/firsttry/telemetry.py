from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional


def _write_report(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def write_report_async(
    path: Path, payload: Dict[str, Any], enabled: bool = True
) -> None:
    """
    Fire-and-forget writer.
    If enabled=False, writes synchronously (useful for tests).
    """
    if not enabled:
        _write_report(path, payload)
        return

    th = threading.Thread(target=_write_report, args=(path, payload), daemon=True)
    th.start()