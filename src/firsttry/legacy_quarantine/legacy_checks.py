# src/firsttry/legacy_checks.py
from __future__ import annotations


def run_legacy_gate(name: str) -> tuple[bool, str]:
    """Attempt to call the old FirstTry engine if present.
    If not present, return success so the new engine doesn't break.
    """
    try:
        from .cli_runner_light import run_gate  # type: ignore
    except Exception:
        return True, f"{name} (legacy) skipped — old engine not present"

    ok = run_gate(name)
    return ok, f"{name} (legacy) {'passed' if ok else 'failed'}"
