"""
Day 7 gates:
- pre_commit gate: fast checks
- pre_push gate: heavier checks (docker, PG drift, hadolint, actionlint)

Public API:
    run_pre_commit_gate() -> list[str]
    run_pre_push_gate() -> list[str]
"""

from __future__ import annotations

import sys
from typing import List


def run_pre_commit_gate() -> List[str]:
    """Return a list of shell commands for a fast pre-commit gate.

    Commands are safe to run locally; some may soft-fail in dev.
    """
    python_exe = sys.executable

    return [
        "ruff check .",
        "mypy .",
        # limit pytest to our core tests dir
        f"{python_exe} -m pytest -q tests/",
        # sqlite import & drift sanity
        (
            f"{python_exe} -c \"from firsttry.db_sqlite import run_sqlite_probe; "
            "res=run_sqlite_probe(); "
            "print('sqlite import_ok=',res['import_ok'],'drift=',res['drift'])\""
        ),
    ]


def run_pre_push_gate() -> List[str]:
    """Return a list of shell commands for a heavier pre-push gate."""
    python_exe = sys.executable
    cmds: List[str] = []

    # start with the pre-commit set
    cmds.extend(run_pre_commit_gate())

    # security scanners (allowed to soft-fail locally)
    cmds.append("bandit -q -r . || true")
    cmds.append("pip-audit || true")

    # docker smoke test
    cmds.append(
        (
            f"{python_exe} -c \"from firsttry.docker_smoke import run_docker_smoke; "
            "print(run_docker_smoke())\""
        )
    )

    # PG drift check (will exit non-zero if destructive drift detected)
    cmds.append(
        (
            f"{python_exe} -c \"from firsttry.db_pg import run_pg_probe; "
            "import os,sys; "
            "try: res=run_pg_probe(allow_destructive=False); print('pg drift:', res); "
            "except RuntimeError as e: print('PG DRIFT BLOCKER:', e); sys.exit(1)\""
        )
    )

    # hadolint and actionlint (external binaries; soft-fail locally)
    cmds.append("hadolint Dockerfile || true")
    cmds.append("actionlint || true")

    return cmds
