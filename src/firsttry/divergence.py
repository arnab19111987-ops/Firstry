from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_report(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def detect_divergence(warm_report: Path | None, full_report: Path | None) -> bool:
    """Return True if the two run reports diverge in meaningful ways.

    For now we consider divergence as JSON inequality. Future work can
    implement smarter heuristics (e.g., ignore timestamps).
    """
    if warm_report is None or full_report is None:
        return False
    warm = _load_report(warm_report)
    full = _load_report(full_report)
    if warm is None or full is None:
        return False
    # Basic equality check; callers may choose to ignore non-deterministic keys.
    return warm != full


def enforce_divergence_exit(warm_report: Path | None, full_report: Path | None) -> None:
    """If divergence detected and current tier is enterprise, raise SystemExit(99).

    This helper is intentionally conservative: if reports are missing or
    unreadable it does nothing.
    """
    try:
        from . import tier

        if not tier.tier_allowed(None, "enterprise"):
            return
    except Exception:
        return

    if detect_divergence(warm_report, full_report):
        raise SystemExit(99)
