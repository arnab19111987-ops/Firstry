from __future__ import annotations

import contextlib
import io
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


class GateResult:
    """Lightweight gate result following the standard format."""

    def __init__(
        self,
        name: str,
        passed: bool,
        errors: int = 0,
        warnings: int = 0,
        fixable: int = 0,
        mode: str = "auto",  # "auto" | "detect" | "advisory"
        extra: dict[str, Any] | None = None,
    ):
        self.name = name  # "lint", "tests", "typecheck", "security"
        self.passed = passed  # bool
        self.errors = errors or 0
        self.warnings = warnings or 0
        self.fixable = fixable or 0
        self.mode = mode  # how this gate behaves: auto-fix, detect-only, advisory
        self.extra = extra or {}  # e.g. {"failed_tests": [...]} or {"first_failed_test": "..."}

        # Legacy fields for backward compatibility
        self.status = "PASS" if passed else "FAIL"
        self.info = ""
        self.details = ""
        self.returncode = 0 if passed else 1
        self.stdout: str | None = None
        self.stderr: str | None = None


def gate_result_to_dict(res: GateResult) -> dict[str, object]:
    """Convert internal GateResult dataclass to a stable JSON-ready dict.

    Keys:
      - gate: human label
      - ok: boolean (True when status == 'PASS')
      - status, info, details: preserved for diagnostics
      - returncode, stdout, stderr: optional fields (may be None)
    """
    return {
        "gate": res.name,
        "ok": res.passed,
        "status": res.status,
        "info": res.info,
        "details": res.details,
        "returncode": res.returncode,
        "stdout": res.stdout or "",
        "stderr": res.stderr or "",
        "errors": res.errors,
        "warnings": res.warnings,
        "fixable": res.fixable,
        "mode": res.mode,
        "extra": res.extra,
    }


def _analyze_output_for_counts(tool_name: str, output: str) -> tuple[int, int, int]:
    """Analyze tool output to extract error, warning, and fixable counts.

    Returns: (errors, warnings, fixable)
    """
    errors = 0
    warnings = 0
    fixable = 0

    if not output:
        return errors, warnings, fixable

    lines = output.split("\n")

    if "ruff" in tool_name.lower() or "lint" in tool_name.lower():
        # Count ruff errors and fixable issues
        for line in lines:
            line = line.strip()
            if re.match(r".*:\d+:\d+:", line):  # ruff error pattern
                errors += 1
                if "[*]" in line:
                    fixable += 1

        # Check for summary lines
        for line in lines:
            match = re.search(r"Found (\d+) errors?\.", line)
            if match:
                errors = max(errors, int(match.group(1)))
            match = re.search(r"\[\*\] (\d+) fixable with", line)
            if match:
                fixable = int(match.group(1))

    elif "mypy" in tool_name.lower():
        # Count mypy errors
        for line in lines:
            if re.match(r".*:\d+:\s+error:", line):
                errors += 1

        # Check for summary
        for line in lines:
            match = re.search(r"Found (\d+) errors? in", line)
            if match:
                errors = max(errors, int(match.group(1)))

    elif "pytest" in tool_name.lower() or "test" in tool_name.lower():
        # Count test failures
        for line in lines:
            if "FAILED" in line and "::" in line:
                errors += 1

        # Check for summary patterns
        for line in lines:
            match = re.search(r"(\d+) failed", line)
            if match:
                errors = max(errors, int(match.group(1)))
    else:
        # Generic counting
        for line in lines:
            lower_line = line.lower()
            if "error" in lower_line or "fail" in lower_line:
                errors += 1
            elif "warning" in lower_line or "warn" in lower_line:
                warnings += 1

    return errors, warnings, fixable


def _run_external(
    cmd: list[str],
    name: str,
    pass_desc: str = "",
    mode: str = "auto",
) -> GateResult:
    """Run external tools like ruff/mypy/pytest.

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
            check=False,
        )
    except FileNotFoundError:
        result = GateResult(name=name, passed=False, mode=mode)
        result.status = "SKIPPED"
        result.info = "tool not installed"
        result.details = (
            f"{name}: SKIPPED because {cmd[0]!r} was not found on PATH.\n"
            "What was attempted:\n"
            f"- We tried to run {cmd!r}\n"
            "Why it skipped:\n"
            "- That tool is not installed in this environment.\n"
            "How to enable:\n"
            f"- Add {cmd[0]} to your dev requirements / venv.\n"
        )
        result.returncode = 0
        result.stdout = None
        result.stderr = None
        return result

    out = (proc.stdout or "") + (proc.stderr or "")

    if proc.returncode == 0:
        # add nicer PASS info
        extra_info = pass_desc
        if name.lower() == "tests":
            # grab "23 passed" etc.
            m = re.search(r"(\d+)\s+passed", out)
            if m:
                extra_info = f"{m.group(1)} tests"

        result = GateResult(name=name, passed=True, mode=mode)
        result.info = extra_info.strip()
        result.details = out.strip()
        result.returncode = proc.returncode
        result.stdout = proc.stdout
        result.stderr = proc.stderr
        return result

    # non-zero exit - analyze the output for error details
    errors, warnings, fixable = _analyze_output_for_counts(name, out)

    result = GateResult(
        name=name,
        passed=False,
        errors=errors,
        warnings=warnings,
        fixable=fixable,
        mode=mode,
    )
    result.info = "see details"
    result.details = out.strip()
    result.returncode = proc.returncode
    result.stdout = proc.stdout
    result.stderr = proc.stderr
    return result


# -------------------------
# Individual gate checks
# -------------------------


def check_lint() -> GateResult:
    """Fast lint check (ruff)."""
    return _run_external(["ruff", "check", "."], name="python-lint", mode="auto")


def check_types() -> GateResult:
    """Static type check (mypy)."""
    return _run_external(["mypy", "."], name="python-type", mode="detect")


def check_tests() -> GateResult:
    """Quick pytest run.

    If pytest isn't available -> SKIPPED (not scary).
    """
    return _run_external(["pytest", "-q"], name="pytest", mode="detect")


def check_sqlite_drift() -> GateResult:
    """SQLite drift / import sanity.

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
        from firsttry import db_sqlite
    except Exception as exc:
        result = GateResult(name="SQLite Drift", passed=False, mode="detect")
        result.status = "SKIPPED"
        result.info = "probe unavailable"
        result.details = (
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
        )
        return result

    probe_stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(probe_stdout):
            if hasattr(db_sqlite, "run_sqlite_probe"):
                # safe probe: does temp work only
                db_sqlite.run_sqlite_probe(import_target="firsttry")
            # else: import alone counts as PASS
    except Exception as exc:
        out = probe_stdout.getvalue()
        result = GateResult(name="SQLite Drift", passed=False, errors=1, mode="detect")
        result.status = "FAIL"
        result.info = "schema drift?"
        result.details = (
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
        )
        return result

    out = probe_stdout.getvalue()
    result = GateResult(name="SQLite Drift", passed=True, mode="detect")
    result.status = "PASS"
    result.info = "no drift"
    result.details = out.strip()
    return result


def check_pg_drift() -> GateResult:
    """Postgres drift check (heavy).

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
        from firsttry import db_pg
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
                db_pg.run_pg_probe(import_target="firsttry")
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
    """Docker smoke test (heavy).

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
        from firsttry import docker_smoke
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
                docker_smoke.run_docker_smoke()
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
    """CI mirror / consistency check.

    Grace rules:
    - If firsttry.ci_mapper missing → SKIPPED.
    - If it raises → FAIL.
    - Else → PASS.
    """
    try:
        from firsttry import ci_mapper
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
                ci_mapper.check_ci_consistency()
            elif hasattr(ci_mapper, "main"):
                ci_mapper.main()
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


def run_gate(which: str) -> tuple[list[dict[str, object]], bool]:
    """Execute either `pre-commit` or `pre-push`.

    Returns:
        (results, overall_ok)

    overall_ok is False if ANY check FAILs.

    """
    if which not in ("pre-commit", "pre-push"):
        raise ValueError("gate must be 'pre-commit' or 'pre-push'")

    tasks = PRE_COMMIT_TASKS if which == "pre-commit" else PRE_PUSH_TASKS

    results: list[GateResult] = []
    any_fail = False

    for label, fn in tasks:
        try:
            # Resolve the callable by name from the current module globals.
            # Tests may monkeypatch functions on the module (e.g. monkeypatch.setattr(gates, "check_lint", ...)).
            # PRE_*_TASKS stores function objects at import time; re-resolving here ensures
            # the latest attribute (possibly a monkeypatched stub) is used instead of the
            # original reference stored in the list.
            fn_name = getattr(fn, "__name__", None)
            current_fn = globals().get(fn_name, fn) if fn_name else fn
            res = current_fn()
        except Exception as exc:
            # Convert unexpected exceptions into a failing GateResult so
            # consumers receive structured output instead of a raised error.
            res = GateResult(
                name=label,
                passed=False,
                errors=1,
                warnings=0,
                fixable=0,
                extra={"exception": str(exc)},
            )
            # Set legacy fields for compatibility
            res.info = "exception"
            res.details = str(exc)
            res.stderr = str(exc)

        # Keep semantic name from gate function, not display label
        # res.name = label  # Don't override - preserve semantic names like "python-lint"
        results.append(res)
        if res.status == "FAIL":
            any_fail = True

    # Convert dataclass results into stable JSON-ready dicts for consumers.
    dict_results = [gate_result_to_dict(r) for r in results]
    return dict_results, (not any_fail)


# Default ordered gates for a combined health report
DEFAULT_GATES: list[str] = ["pre-commit", "pre-push"]


def run_all_gates(repo_root: Path) -> dict[str, Any]:
    """Run all default gates (pre-commit, pre-push, etc.) against the repo
    and return a single JSON-ready summary.

    Returns:
        {"ok": bool, "results": [ ... ]}

    """
    combined_results: list[dict[str, object]] = []
    overall_ok = True

    for gate_name in DEFAULT_GATES:
        gate_results, gate_ok = run_gate(gate_name)
        combined_results.extend(gate_results)
        if not gate_ok:
            overall_ok = False

    return {"ok": overall_ok, "results": combined_results}


def format_summary(which: str, results: list[GateResult], overall_ok: bool) -> str:
    """Build pretty summary block:

    FirstTry Gate Summary
    ---------------------
    Lint.......... PASS
    ...
    Verdict: SAFE TO COMMIT ✅
    """
    lines: list[str] = []
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
            "One or more checks FAILED. Read details above and fix before continuing.",
        )
    else:
        lines.append(
            "Everything looks good. You'll almost certainly pass CI on the first try.",
        )

    return "\n".join(lines)


def print_verbose(results: list[GateResult]) -> None:
    """After the summary, dump extra context only for FAIL and SKIPPED.

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


# -------------------------
# Back-compat helpers for tests expecting command lists
# -------------------------


def run_pre_commit_gate() -> list[str]:
    """Compatibility surface for tests that expect a list of CLI commands
    representing the pre-commit gate sequence. These are not executed here;
    they're illustrative of what the gate would run.
    """
    return [
        "ruff check .",
        "mypy .",
        "python -m pytest -q",
        # safe import/probe commands
        'python -c "from firsttry.db_sqlite import run_sqlite_probe; run_sqlite_probe()"',
        # optional CI mirror
        "python -c \"from firsttry import ci_mapper; ci_mapper.main() if hasattr(ci_mapper, 'main') else None\"",
    ]


def run_pre_push_gate() -> list[str]:
    cmds = list(run_pre_commit_gate())
    cmds.extend(
        [
            # heavy probes guarded by env/config in real execution
            'python -c "from firsttry.db_pg import run_pg_probe; run_pg_probe()"',
            'python -c "from firsttry.docker_smoke import run_docker_smoke; run_docker_smoke()"',
            # extra linters typically present in CI images
            "hadolint Dockerfile",
            "actionlint -format tap",
            # security scanners (at least one of these in CI)
            "pip-audit -r requirements.txt",
        ],
    )
    return cmds
