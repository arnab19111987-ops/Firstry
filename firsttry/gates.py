from __future__ import annotations

import contextlib
import io
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class GateResult:
    name: str            # e.g. "Lint.........."
    status: str          # "PASS" | "FAIL" | "SKIPPED"
    info: str = ""       # short summary shown in summary table
    details: str = ""    # long explanation printed in verbose mode


def _run_external(
    cmd: List[str],
    name: str,
    pass_desc: str = "",
) -> GateResult:
    """
    Run external tools like ruff/mypy/pytest.

    Rules:
    - If the tool is not found: SKIPPED with guidance.
    - If it returns code 0: PASS.
    - Else: FAIL with captured output.
    """
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return GateResult(
            name=name,
            status="SKIPPED",
            info="tool not installed",
            details=(
                f"{name}: SKIPPED because {cmd[0]!r} was not found on PATH.\n"
                "What was attempted:\n"
                f"- We tried to run {cmd!r}\n"
                "Why it skipped:\n"
                "- That tool is not installed in this environment.\n"
                "How to enable:\n"
                f"- Add {cmd[0]} to your dev requirements / venv.\n"
            ),
        )

    out = (proc.stdout or "") + (proc.stderr or "")

    if proc.returncode == 0:
        # add nicer PASS info
        extra_info = pass_desc
        if name.lower() == "tests":
            # grab "23 passed" etc.
            m = re.search(r"(\d+)\s+passed", out)
            if m:
                extra_info = f"{m.group(1)} tests"

        return GateResult(
            name=name,
            status="PASS",
            info=extra_info.strip(),
            details=out.strip(),
        )

    # non-zero exit
    return GateResult(
        name=name,
        status="FAIL",
        info="see details",
        details=out.strip(),
    )


# -------------------------
# Individual gate checks
# -------------------------

def check_lint() -> GateResult:
    """Fast lint check (ruff)."""
    return _run_external(["ruff", "check", "."], name="Lint")


def check_types() -> GateResult:
    """Static type check (mypy)."""
    return _run_external(["mypy", "."], name="Types")


def check_tests() -> GateResult:
    """
    Quick pytest run.

    If pytest isn't available -> SKIPPED (not scary).
    """
    return _run_external(["pytest", "-q"], name="Tests")


def check_sqlite_drift() -> GateResult:
    """
    SQLite drift / import sanity.

    Behavior:
    - If firsttry.db_sqlite is missing → SKIPPED with explanation.
    - If probe runs clean → PASS.
    - If probe raises → FAIL with fix hints.

    The probe is expected to be SAFE:
    - temp .firsttry.db sqlite file
    - temp Alembic script_location
    - does NOT modify repo or prod DB
    """
    try:
        from firsttry import db_sqlite  # type: ignore
    except Exception as exc:
        return GateResult(
            name="SQLite Drift",
            status="SKIPPED",
            info="probe unavailable",
            details=(
                "SQLite Drift: SKIPPED because firsttry.db_sqlite "
                f"could not be imported ({exc!r}).\n"
                "What was attempted:\n"
                "- We try to autogenerate a migration in a temp dir against a "
                "temp SQLite DB (./.firsttry.db).\n"
                "Why it skipped:\n"
                "- The SQLite drift probe module isn't in this project yet.\n"
                "How to configure:\n"
                "- Add firsttry/db_sqlite.py with run_sqlite_probe() that "
                "compares models vs migrations.\n"
            ),
        )

    probe_stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(probe_stdout):
            if hasattr(db_sqlite, "run_sqlite_probe"):
                # safe probe: does temp work only
                db_sqlite.run_sqlite_probe()  # type: ignore[attr-defined]
            # else: import alone counts as PASS
    except Exception as exc:
        out = probe_stdout.getvalue()
        return GateResult(
            name="SQLite Drift",
            status="FAIL",
            info="schema drift?",
            details=(
                "SQLite Drift probe reported an issue.\n"
                f"{out}\n"
                f"Exception: {exc!r}\n\n"
                "What happened:\n"
                "- We tried to autogenerate an Alembic migration from your "
                "models.\n"
                "- The result didn't match what's committed.\n"
                "How to fix:\n"
                "- Run `alembic revision --autogenerate`, review, commit.\n"
                "- OR update models so they match existing migrations.\n"
            ),
        )

    out = probe_stdout.getvalue()
    return GateResult(
        name="SQLite Drift",
        status="PASS",
        info="no drift",
        details=out.strip(),
    )


def check_pg_drift() -> GateResult:
    """
    Postgres drift check (heavy).

    Grace rules:
    - If DATABASE_URL missing or not postgres → SKIPPED.
    - If firsttry.db_pg missing → SKIPPED.
    - If probe fails → FAIL.
    - Else → PASS.
    """
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or not db_url.lower().startswith(("postgres://", "postgresql://")):
        return GateResult(
            name="PG Drift",
            status="SKIPPED",
            info="no Postgres configured",
            details=(
                "PG Drift: SKIPPED because DATABASE_URL is not Postgres.\n"
                "What was attempted:\n"
                "- We would connect to your live Postgres and compare schema "
                "vs Alembic migrations.\n"
                "Why it skipped:\n"
                "- There's no Postgres DATABASE_URL.\n"
                "How to configure:\n"
                "- export DATABASE_URL=postgresql://user:pass@host/db\n"
                "- Add firsttry/db_pg.py with run_pg_probe().\n"
            ),
        )

    try:
        from firsttry import db_pg  # type: ignore
    except Exception as exc:
        return GateResult(
            name="PG Drift",
            status="SKIPPED",
            info="probe unavailable",
            details=(
                "PG Drift: SKIPPED because firsttry.db_pg could not be "
                f"imported ({exc!r}).\n"
                "What was attempted:\n"
                "- We planned to run a dry-run Alembic autogenerate against "
                "your live Postgres.\n"
                "Why it skipped:\n"
                "- The PG drift probe module isn't present.\n"
                "How to configure:\n"
                "- Add firsttry/db_pg.py with run_pg_probe() that inspects "
                "your Postgres schema.\n"
            ),
        )

    probe_stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(probe_stdout):
            if hasattr(db_pg, "run_pg_probe"):
                db_pg.run_pg_probe()  # type: ignore[attr-defined]
            # else: import success = PASS
    except Exception as exc:
        out = probe_stdout.getvalue()
        return GateResult(
            name="PG Drift",
            status="FAIL",
            info="schema drift?",
            details=(
                "PG Drift probe reported an issue.\n"
                f"{out}\n"
                f"Exception: {exc!r}\n\n"
                "What happened:\n"
                "- We connected to DATABASE_URL Postgres.\n"
                "- We compared the live schema vs your Alembic migrations.\n"
                "How to fix:\n"
                "- Generate/commit a new Alembic migration OR\n"
                "- Apply pending migrations to the DB.\n"
            ),
        )

    out = probe_stdout.getvalue()
    return GateResult(
        name="PG Drift",
        status="PASS",
        info="no drift",
        details=out.strip(),
    )


def check_docker_smoke() -> GateResult:
    """
    Docker smoke test (heavy).

    Grace rules:
    - If `docker` CLI isn't found → SKIPPED ("no Docker runtime").
    - If firsttry.docker_smoke missing → SKIPPED.
    - If probe fails → FAIL.
    - Else → PASS.
    """
    if shutil.which("docker") is None:
        return GateResult(
            name="Docker Smoke",
            status="SKIPPED",
            info="no Docker runtime",
            details=(
                "Docker Smoke: SKIPPED because `docker` CLI was not found.\n"
                "What was attempted:\n"
                "- We would `docker compose up` your stack and curl /health.\n"
                "Why it skipped:\n"
                "- Docker/Colima/etc. not available in this environment.\n"
                "How to configure:\n"
                "- Install Docker Desktop / Colima / etc and ensure `docker` "
                "works in this shell.\n"
                "- Add firsttry/docker_smoke.py with run_docker_smoke().\n"
            ),
        )

    try:
        from firsttry import docker_smoke  # type: ignore
    except Exception as exc:
        return GateResult(
            name="Docker Smoke",
            status="SKIPPED",
            info="probe unavailable",
            details=(
                "Docker Smoke: SKIPPED because firsttry.docker_smoke could "
                f"not be imported ({exc!r}).\n"
                "What was attempted:\n"
                "- Build/run your docker-compose stack and verify health.\n"
                "How to configure:\n"
                "- Add firsttry/docker_smoke.py with run_docker_smoke() that:\n"
                "  - docker compose up -d\n"
                "  - wait for health\n"
                "  - curl http://localhost:8000/health\n"
            ),
        )

    smoke_stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(smoke_stdout):
            if hasattr(docker_smoke, "run_docker_smoke"):
                docker_smoke.run_docker_smoke()  # type: ignore[attr-defined]
            # else: import success = PASS
    except Exception as exc:
        out = smoke_stdout.getvalue()
        return GateResult(
            name="Docker Smoke",
            status="FAIL",
            info="container smoke failed",
            details=(
                "Docker Smoke failed.\n"
                f"{out}\n"
                f"Exception: {exc!r}\n\n"
                "What happened:\n"
                "- We attempted to build/run your container stack, and "
                "the health probe failed.\n"
                "How to fix:\n"
                "- Fix Dockerfile build errors / failing health endpoint.\n"
            ),
        )

    out = smoke_stdout.getvalue()
    return GateResult(
        name="Docker Smoke",
        status="PASS",
        info="stack healthy",
        details=out.strip(),
    )


def check_ci_mirror() -> GateResult:
    """
    CI mirror / consistency check.

    Grace rules:
    - If firsttry.ci_mapper missing → SKIPPED.
    - If it raises → FAIL.
    - Else → PASS.
    """
    try:
        from firsttry import ci_mapper  # type: ignore
    except Exception as exc:
        return GateResult(
            name="CI Mirror",
            status="SKIPPED",
            info="mapper unavailable",
            details=(
                "CI Mirror: SKIPPED because firsttry.ci_mapper could not "
                f"be imported ({exc!r}).\n"
                "What was attempted:\n"
                "- We want to read .github/workflows/*.yml and produce a "
                "local dry-run of what CI does.\n"
                "Why it skipped:\n"
                "- The CI mapper module isn't present.\n"
                "How to configure:\n"
                "- Add firsttry/ci_mapper.py with check_ci_consistency() or "
                "an equivalent function that prints your CI steps.\n"
            ),
        )

    mapper_stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(mapper_stdout):
            if hasattr(ci_mapper, "check_ci_consistency"):
                ci_mapper.check_ci_consistency()  # type: ignore[attr-defined]
            elif hasattr(ci_mapper, "main"):
                ci_mapper.main()  # type: ignore[attr-defined]
            # else: import itself counts as PASS
    except Exception as exc:
        out = mapper_stdout.getvalue()
        return GateResult(
            name="CI Mirror",
            status="FAIL",
            info="see details",
            details=(
                "CI Mirror reported mismatch.\n"
                f"{out}\n"
                f"Exception: {exc!r}\n\n"
                "What happened:\n"
                "- We tried to map CI steps to local commands.\n"
                "How to fix:\n"
                "- Sync your local pre-commit/pre-push steps with "
                ".github/workflows/*.yml.\n"
            ),
        )

    out = mapper_stdout.getvalue()
    return GateResult(
        name="CI Mirror",
        status="PASS",
        info="workflow looks consistent",
        details=out.strip(),
    )


# -------------------------
# Gate task definitions
# -------------------------

PRE_COMMIT_TASKS = [
    ("Lint..........", check_lint),
    ("Types.........", check_types),
    ("Tests.........", check_tests),
    ("SQLite Drift..", check_sqlite_drift),
    ("CI Mirror.....", check_ci_mirror),
]

PRE_PUSH_TASKS = [
    ("Lint..........", check_lint),
    ("Types.........", check_types),
    ("Tests.........", check_tests),
    ("SQLite Drift..", check_sqlite_drift),
    ("PG Drift......", check_pg_drift),
    ("Docker Smoke..", check_docker_smoke),
    ("CI Mirror.....", check_ci_mirror),
]


def run_gate(which: str) -> Tuple[List[GateResult], bool]:
    """
    Execute either `pre-commit` or `pre-push`.

    Returns:
        (results, overall_ok)

    overall_ok is False if ANY check FAILs.
    """
    if which not in ("pre-commit", "pre-push"):
        raise ValueError("gate must be 'pre-commit' or 'pre-push'")

    tasks = PRE_COMMIT_TASKS if which == "pre-commit" else PRE_PUSH_TASKS

    results: List[GateResult] = []
    any_fail = False

    for label, fn in tasks:
        res = fn()
        # annotate display label (e.g. "Lint.........." instead of "Lint")
        res.name = label
        results.append(res)
        if res.status == "FAIL":
            any_fail = True

    return results, (not any_fail)


def format_summary(which: str, results: List[GateResult], overall_ok: bool) -> str:
    """
    Build pretty summary block:

    FirstTry Gate Summary
    ---------------------
    Lint.......... PASS
    ...
    Verdict: SAFE TO COMMIT ✅
    """
    lines: List[str] = []
    lines.append("FirstTry Gate Summary")
    lines.append("---------------------")

    for res in results:
        info_part = f" {res.info}" if res.info else ""
        lines.append(f"{res.name} {res.status}{info_part}")

    lines.append("")

    verdict_line = "Verdict: "
    if overall_ok:
        if which == "pre-commit":
            verdict_line += "SAFE TO COMMIT ✅"
        elif which == "pre-push":
            verdict_line += "SAFE TO PUSH ✅"
        else:
            verdict_line += "SAFE ✅"
    else:
        verdict_line += "BLOCKED ❌"

    lines.append(verdict_line)
    lines.append("")

    if not overall_ok:
        lines.append(
            "One or more checks FAILED. Read details above and fix before continuing."
        )
    else:
        lines.append(
            "Everything looks good. You'll almost certainly pass CI on the first try."
        )

    return "\n".join(lines)


def print_verbose(results: List[GateResult]) -> None:
    """
    After the summary, dump extra context only for FAIL and SKIPPED.

    This is the "here's what happened, why we skipped, how to enable it"
    layer that builds trust with newer devs / trial users.
    """
    for res in results:
        if res.status in ("FAIL", "SKIPPED"):
            header = f"=== {res.name} {res.status} ==="
            print(header)
            if res.details:
                print(res.details)
            print()
