"""
Day 6 PG drift:
- If DATABASE_URL (or provided db_url) looks like Postgres,
  run Alembic autogen in temp dir.
- Parse resulting revision for destructive ops.

Public API:
    run_pg_probe(import_target="backend", allow_destructive=False, db_url=None) -> dict
    parse_destructive_ops(script_text: str) -> dict
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db_sqlite import _write_temp_alembic_env  # reuse env writer from Day 4

DESTRUCTIVE_PATTERNS = (
    "op.drop_table",
    "op.drop_column",
    "op.drop_constraint",
    "DROP TABLE",
    "DROP COLUMN",
    "DROP CONSTRAINT",
)


def parse_destructive_ops(script_text: str) -> Dict[str, List[str]]:
    """
    Heuristic parser for destructive operations in an Alembic revision script.
    Returns:
        {
          "destructive": [...lines...],
          "non_destructive": [...lines...],
        }
    """
    destructive: List[str] = []
    non_destructive: List[str] = []

    for line in script_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(pat in stripped for pat in DESTRUCTIVE_PATTERNS):
            destructive.append(stripped)
        else:
            # ignore comments, metadata lines, etc. but keep ops.* create/alter
            if stripped.startswith("op.") or "CREATE TABLE" in stripped:
                non_destructive.append(stripped)

    return {
        "destructive": destructive,
        "non_destructive": non_destructive,
    }


def _is_postgres_url(url: str) -> bool:
    return url.startswith("postgres://") or url.startswith("postgresql")


def _alembic_autogen_pg(import_target: str, db_url: str) -> dict:
    """
    Almost identical to sqlite autogen, but we inline it here so we can
    enrich output for PG.
    """
    try:
        from alembic import command
        from alembic.config import Config
    except ImportError as e:
        return {
            "skipped": True,
            "reason": f"Alembic not available: {e}",
        }

    with tempfile.TemporaryDirectory(prefix="firsttry_pg_alembic_") as tmp:
        tmp_path = Path(tmp)
        _write_temp_alembic_env(tmp_path, import_target)

        cfg = Config()
        cfg.set_main_option("script_location", str(tmp_path))
        cfg.set_main_option("sqlalchemy.url", db_url)

        message = f"firsttry_autogen_probe_{int(time.time())}"
        command.revision(
            cfg,
            message=message,
            autogenerate=True,
        )

        versions_dir = tmp_path / "versions"
        rev_files = list(versions_dir.glob("*.py"))
        if not rev_files:
            return {
                "has_drift": False,
                "script_text": "",
                "skipped": False,
            }

        rev_file = rev_files[0]
        script_text = rev_file.read_text(encoding="utf-8")

        # Presence of any upgrade ops means drift.
        has_drift = "def upgrade()" in script_text and "pass" not in script_text

        ops = parse_destructive_ops(script_text)

        return {
            "has_drift": has_drift,
            "script_text": script_text,
            "skipped": False,
            "ops": ops,
        }


def run_pg_probe(
    import_target: str = "backend",
    allow_destructive: bool = False,
    db_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns dict with keys:
    {
      "skipped": bool,
      "reason": str | None,
      "has_drift": bool,
      "ops": { "destructive": [...], "non_destructive": [...] },
    }

    Raises RuntimeError if destructive ops exist AND not allow_destructive.
    """
    if db_url is None:
        db_url = os.environ.get("DATABASE_URL")

    if not db_url or not _is_postgres_url(db_url):
        return {
            "skipped": True,
            "reason": "DATABASE_URL not Postgres, skipping PG drift probe",
            "has_drift": False,
            "ops": {"destructive": [], "non_destructive": []},
        }

    res = _alembic_autogen_pg(import_target, db_url)
    if res.get("skipped"):
        return {
            "skipped": True,
            "reason": res.get("reason", "Alembic skipped"),
            "has_drift": False,
            "ops": {"destructive": [], "non_destructive": []},
        }

    ops = res.get("ops", {"destructive": [], "non_destructive": []})
    destructive_ops = ops["destructive"]

    if destructive_ops and not allow_destructive:
        # Hard fail
        raise RuntimeError(
            "Destructive migration ops detected: " + "; ".join(destructive_ops)
        )

    return {
        "skipped": False,
        "reason": None,
        "has_drift": res["has_drift"],
        "ops": ops,
    }
