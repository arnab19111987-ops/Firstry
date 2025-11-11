from __future__ import annotations

from pathlib import Path

from .base import Gate, GateResult


class DepsLockGate(Gate):
    """MVP: detect obvious Python dependency drift.
    Rules:
    - if requirements.txt exists but no lock -> warn
    - if poetry.lock exists but no pyproject.toml -> warn
    - if both exist, compare mtime and size as cheap heuristic
    """

    gate_id = "deps:lock"
    patterns = (
        "requirements.txt",
        "requirements.lock",
        "poetry.lock",
        "pyproject.toml",
    )

    def run(self, root: Path) -> GateResult:
        req = root / "requirements.txt"
        lock_req = root / "requirements.lock"
        poetry = root / "pyproject.toml"
        poetry_lock = root / "poetry.lock"

        msgs: list[str] = []
        ok = True

        # Case 1: classic pip
        if req.exists():
            if not lock_req.exists():
                ok = False
                msgs.append("requirements.txt exists but requirements.lock is missing.")
            else:
                # cheap drift check — we don't parse yet
                try:
                    if lock_req.stat().st_mtime < req.stat().st_mtime:
                        ok = False
                        msgs.append(
                            "requirements.lock is older than requirements.txt (run lock update).",
                        )
                except Exception:
                    # stat issues shouldn't crash gate
                    pass

        # Case 2: poetry
        if poetry.exists():
            if not poetry_lock.exists():
                ok = False
                msgs.append(
                    "pyproject.toml exists but poetry.lock is missing (run `poetry lock`).",
                )
            else:
                try:
                    if poetry_lock.stat().st_mtime < poetry.stat().st_mtime:
                        ok = False
                        msgs.append(
                            "poetry.lock is older than pyproject.toml (run `poetry lock`).",
                        )
                except Exception:
                    pass

        if not msgs:
            msgs.append("dependency locks look consistent (MVP check).")

        return GateResult(
            gate_id=self.gate_id,
            ok=ok,
            output="\n".join(msgs),
            watched_files=list(self.patterns),
        )
