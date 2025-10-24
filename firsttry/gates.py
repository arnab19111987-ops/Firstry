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


def run_pre_commit_gate() -> list[str]:
    """
    Fast stuff only. (Soft-fail in local dev; CI can hard-fail.)
    We just return the commands in order.
    """
    python_exe = sys.executable

    return [
        "ruff check .",
        "mypy .",
        # run tests quickly (could be -q or specific subset)
        f"{python_exe} -m pytest -q",
        # sqlite import & drift sanity
        (
            f'{python_exe} -c "from firsttry.db_sqlite import run_sqlite_probe; '
            "res=run_sqlite_probe(); "
            "print('sqlite import_ok=',res['import_ok'],'drift=',res['drift'])\""
        ),
    ]


def run_pre_push_gate() -> list[str]:
    """
    Heavier stuff. Should be called before git push OR in CI.
    Includes docker smoke, PG drift (if DATABASE_URL is pg), hadolint, actionlint
    """
    python_exe = sys.executable
    cmds: list[str] = []

    # start with pre-commit set
    cmds.extend(run_pre_commit_gate())

    # basic security scanners (you can expand these for bandit, pip-audit, etc.)
    cmds.append("bandit -q -r . || true")
    cmds.append("pip-audit || true")

    # docker smoke test
    cmds.append(
        (
            f'{python_exe} -c "from firsttry.docker_smoke import run_docker_smoke; '
            "print(run_docker_smoke())\""
        )
    )

    # PG drift check (will raise RuntimeError if destructive unless allowed)
    cmds.append(
        (
            f'{python_exe} -c "from firsttry.db_pg import run_pg_probe; '
            "import os,sys; "
            "try:\n"
            "    res=run_pg_probe(allow_destructive=False);\n"
            "    print('pg drift:',res)\n"
            "except RuntimeError as e:\n"
            "    print('PG DRIFT BLOCKER:',e); sys.exit(1)\""
        )
    )

    # hadolint and actionlint (external binaries normally installed separately)
    cmds.append("hadolint Dockerfile || true")
    cmds.append("actionlint || true")

    return cmds
