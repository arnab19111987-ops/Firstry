from __future__ import annotations

import os
import re
from typing import Dict, List, Any


# Regexes for destructive ops
_DROP_TABLE_FUNC = re.compile(r"op\.drop_table\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
_DROP_COLUMN_FUNC = re.compile(
    r"op\.drop_column\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
_RAW_DROP_TABLE_SQL = re.compile(
    r"\bDROP\s+TABLE\b\s+([A-Za-z0-9_\".]+)", re.IGNORECASE
)


def parse_destructive_ops(script_text: str) -> Dict[str, List[str]]:
    destructive: List[str] = []
    non_destructive: List[str] = []

    for line in script_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if _DROP_TABLE_FUNC.search(stripped):
            destructive.append(stripped)
            continue
        if _DROP_COLUMN_FUNC.search(stripped):
            destructive.append(stripped)
            continue
        if _RAW_DROP_TABLE_SQL.search(stripped):
            destructive.append(stripped)
            continue

        non_destructive.append(stripped)

    return {"destructive": destructive, "non_destructive": non_destructive}


def _alembic_autogen_pg(import_target: str, db_url: str) -> Dict[str, Any]:
    script_text = ""
    ops = parse_destructive_ops(script_text)
    return {
        "has_drift": False,
        "script_text": script_text,
        "skipped": False,
        "ops": ops,
    }


def run_pg_probe(import_target: str, allow_destructive: bool = True) -> Dict[str, Any]:
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url or not db_url.lower().startswith(("postgres://", "postgresql://")):
        return {"skipped": True, "reason": "DATABASE_URL not Postgres or not set"}

    result = _alembic_autogen_pg(import_target, db_url)
    ops = result.get("ops", {"destructive": [], "non_destructive": []})
    destructive_ops = ops.get("destructive", [])
    if destructive_ops and not allow_destructive:
        raise RuntimeError(
            "Destructive Postgres migration detected: " + "; ".join(destructive_ops)
        )

    return {
        "skipped": False,
        "has_drift": bool(result.get("has_drift", False)),
        "ops": ops,
        "script_text": result.get("script_text", ""),
    }
