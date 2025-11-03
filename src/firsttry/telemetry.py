from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict

try:  # stdlib HTTP client
    from urllib import request
except Exception:  # pragma: no cover
    request = None  # type: ignore


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


# --- Telemetry (opt-in) --------------------------------------------------

TELEMETRY_URL = os.environ.get("FIRSTTRY_TELEMETRY_URL", "https://telemetry.firsttry.run/collect")
STATUS_FILE = Path(".firsttry/telemetry_status.json")


def _write_status(ok: bool, message: str = "") -> None:
    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATUS_FILE.write_text(json.dumps({
            "ok": ok,
            "message": message,
            "ts": int(time.time()),
        }, indent=2))
    except Exception:
        pass


def send_report(report: Dict[str, Any]) -> None:
    """Best-effort telemetry sender using stdlib HTTP; never raises."""
    try:
        if request is None:
            _write_status(False, "urllib not available")
            return
        data = json.dumps({
            "schema_version": report.get("schema_version"),
            "tier": report.get("tier"),
            "profile": report.get("profile"),
            "timing": report.get("timing", {}),
            "checks": [
                {"id": c.get("id"), "status": c.get("status"), "locked": c.get("locked", False)}
                for c in report.get("checks", [])
            ],
        }).encode("utf-8")
        req = request.Request(TELEMETRY_URL, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with request.urlopen(req, timeout=3) as resp:  # nosec - fixed URL
            ok = 200 <= getattr(resp, 'status', 200) < 300
            _write_status(ok, f"status={getattr(resp, 'status', 200)}")
    except Exception as e:  # pragma: no cover (network)
        _write_status(False, str(e))