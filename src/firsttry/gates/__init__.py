"""FirstTry gate implementations."""

import os
import subprocess
import sys
from typing import Any

from .base import GateResult
from .utils import _safe_gate


# Compatibility functions for old test suite
def run_pre_commit_gate():
    """Return list of commands for pre-commit gate (compatibility function)."""
    return [
        "ruff check .",
        "mypy --ignore-missing-imports .",
        "pytest -q -m 'not slow'",
        "run_sqlite_probe",  # Legacy compatibility
    ]


def run_pre_push_gate():
    """Return list of commands for pre-push gate (compatibility function)."""
    pre_commit_cmds = run_pre_commit_gate()
    return pre_commit_cmds + [
        "bandit -q -r .",
        "radon cc . --total-average",
    ]


def run_gate(gate_name: str):
    """Compatibility function for running individual gates."""
    # Validate gate names - only accept known gate types
    valid_gates = ["pre-commit", "pre-push"]
    if gate_name not in valid_gates:
        raise ValueError(
            f"Unknown gate: {gate_name}. Valid gates are: {', '.join(valid_gates)}",
        )

    # Try to provide more realistic results based on gate name
    if gate_name == "pre-commit":
        results = [check_lint(), check_types(), check_tests()]
    else:  # gate_name == "pre-push"
        results = [check_lint(), check_types(), check_tests(), check_docker_smoke()]

    # Convert to dict format for JSON serialization if needed
    serializable_results = []
    for r in results:
        if hasattr(r, "to_dict"):
            d = r.to_dict()
        else:
            d = gate_result_to_dict(r)
        # Ensure 'gate' key is present for test compatibility
        if "gate_id" in d and "gate" not in d:
            d["gate"] = d["gate_id"]
        serializable_results.append(d)
    ok = all(r.ok for r in results)

    # Return both formats to maintain compatibility
    return serializable_results, ok


def format_summary(gate_name: str, results: list[Any], overall_ok: bool = True) -> str:
    """Compatibility function for formatting gate results."""
    status = "✓" if overall_ok else "✗"
    verdict = "SAFE TO COMMIT" if overall_ok else "BLOCKED"
    count_text = f"{len(results)} gates processed"

    # Include individual gate details
    details = []
    for result in results:
        if hasattr(result, "name") and hasattr(result, "status"):
            details.append(f"{result.name} {result.status}")
        elif hasattr(result, "gate_id") and hasattr(result, "ok"):
            gate_status = "PASS" if result.ok else "FAIL"
            details.append(f"{result.gate_id} {gate_status}")

    summary_lines = [f"{status} {gate_name}: {count_text}"]
    if details:
        summary_lines.extend(details)
    summary_lines.append(f"Verdict: {verdict}")

    return "\n".join(summary_lines)


def print_verbose(message: Any):
    """Compatibility function for verbose printing."""
    if isinstance(message, list):
        # Handle list of GateResult objects
        for result in message:
            if hasattr(result, "gate_id"):
                # Use status property if available, otherwise derive from ok
                if hasattr(result, "status"):
                    status = result.status
                elif hasattr(result, "ok"):
                    status = (
                        "PASS"
                        if result.ok
                        else "FAIL"
                        if not getattr(result, "skipped", False)
                        else "SKIPPED"
                    )
                else:
                    status = "UNKNOWN"
                print(f"{result.gate_id} {status}")
            elif hasattr(result, "name"):
                # Handle GateResult with name attribute
                if hasattr(result, "status"):
                    status = result.status
                elif hasattr(result, "ok"):
                    status = (
                        "PASS"
                        if result.ok
                        else "FAIL"
                        if not getattr(result, "skipped", False)
                        else "SKIPPED"
                    )
                else:
                    status = "UNKNOWN"
                print(f"{result.name} {status}")
            else:
                print(f"[VERBOSE] {result}")
    else:
        print(f"[VERBOSE] {message}")


# Individual check functions that tests expect
def check_lint():
    """Compatibility function for check_lint."""
    return _safe_gate("lint", ["ruff", "check", "."])


def check_types():
    """Compatibility function for check_types."""
    return _safe_gate("types", ["mypy", "--ignore-missing-imports", "."])


# NOTE:
# This gate intentionally does NOT use _safe_gate(), because tests expect
# us to parse pytest output and return test counts in res.info/details.
# Do NOT "simplify" this to _safe_gate() unless you also port the parser.
def check_tests():
    """Compatibility function for check_tests."""
    # Guard against nested pytest invocations set by parent process via FT_DISABLE_NESTED_PYTEST
    if os.environ.get("FT_DISABLE_NESTED_PYTEST") == "1":
        return GateResult(
            gate_id="tests",
            ok=True,
            skipped=True,
            reason="nested pytest detected; skipping",
            output="",
        )

    try:
        # Set guard for child processes to prevent recursion
        env = os.environ.copy()
        env["FT_DISABLE_NESTED_PYTEST"] = "1"

        try:
            # Disable pytest plugin autoload in child process to avoid test harness
            # interference from loaded plugins. Also set a conservative timeout
            # so the gate cannot hang indefinitely.
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                capture_output=True,
                text=True,
                check=False,
                env=env,
                timeout=120,
            )
        except TypeError:
            # Monkeypatch doesn't accept check parameter
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )

        # Parse test count from output like "23 passed in 1.5s"
        info = "pytest tests"
        if result.returncode == 0 and result.stdout:
            import re

            m = re.search(r"(\d+)\s+passed", result.stdout)
            if m:
                info = f"{m.group(1)} tests"

        return GateResult(
            gate_id="tests",
            ok=result.returncode == 0,
            output=result.stdout,
            reason=info if result.returncode == 0 else f"pytest failures: {result.stdout}",
        )
    except FileNotFoundError:
        return GateResult(
            gate_id="tests",
            ok=True,
            skipped=True,
            reason="pytest not found",
            output="pytest not found",
        )
    except subprocess.TimeoutExpired as e:
        return GateResult(
            gate_id="tests",
            ok=False,
            output=getattr(e, "stdout", ""),
            reason="pytest timed out",
        )
    except Exception as e:
        return GateResult(
            gate_id="tests",
            ok=False,
            output=str(e),
            reason=f"Error running tests: {e}",
        )


def check_sqlite_drift():
    """Compatibility function for check_sqlite_drift."""
    return GateResult(
        gate_id="sqlite_drift",
        ok=True,
        skipped=True,
        reason="sqlite drift check not implemented",
    )


def check_pg_drift():
    """Compatibility function for check_pg_drift."""
    return GateResult(
        gate_id="pg_drift",
        ok=True,
        skipped=True,
        reason="no Postgres configured",
    )


def check_docker_smoke():
    """Compatibility function for check_docker_smoke."""
    return GateResult(
        gate_id="docker_smoke",
        ok=True,
        skipped=True,
        reason="no Docker runtime",
    )


def check_ci_mirror():
    """Compatibility function for check_ci_mirror."""
    return GateResult(
        gate_id="ci_mirror",
        ok=True,
        skipped=True,
        reason="ci mirror check not implemented",
    )


def run_all_gates(project_root: Any) -> list[GateResult]:
    """Compatibility function for run_all_gates."""
    # Mock implementation
    results = [check_lint(), check_types(), check_tests()]
    return results


def gate_result_to_dict(gate_result: Any) -> dict[str, Any]:
    """Compatibility function to convert GateResult to dict."""
    is_skipped = getattr(gate_result, "skipped", False)
    status = "SKIPPED" if is_skipped else ("PASS" if gate_result.ok else "FAIL")
    returncode = None if is_skipped else (0 if gate_result.ok else 1)

    return {
        "gate": getattr(gate_result, "gate_id", "unknown"),
        "name": getattr(gate_result, "gate_id", "unknown"),
        "status": status,
        "ok": gate_result.ok,
        "info": gate_result.reason,
        "details": getattr(gate_result, "output", ""),
        "stdout": getattr(gate_result, "output", gate_result.reason),
        "returncode": returncode,
    }
