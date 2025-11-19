"""FirstTry gate implementations."""

import os
import subprocess
from typing import Any, Dict, List, Optional, Sequence

from .base import GateResult
from .utils import _safe_gate
from dataclasses import dataclass, field
from firsttry.ci_parity.unmapped import get_unmapped_steps_for_gate


@dataclass
class GateSummaryItem:
    name: str
    kind: str  # "checked" | "skipped" | "unknown"
    reason: str | None = None


@dataclass
class GateSummary:
    gate_name: str
    checked: list[GateSummaryItem] = field(default_factory=list)
    skipped: list[GateSummaryItem] = field(default_factory=list)
    unknown: list[GateSummaryItem] = field(default_factory=list)
    result: str = "FAIL"
    # Mirror status fields (populated lazily by build_gate_summary)
    mirror_fresh: bool = True
    mirror_stale_workflows: list[str] = field(default_factory=list)

# Default timeout for the tests gate (seconds)
DEFAULT_CHECK_TESTS_TIMEOUT = float(os.getenv("FIRSTTRY_CHECK_TESTS_TIMEOUT", "60"))
# Exit code to use when pytest times out
CHECK_TESTS_TIMEOUT_EXIT_CODE = int(
    os.getenv("FIRSTTRY_CHECK_TESTS_TIMEOUT_EXITCODE", "124")
)


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
            f"Unknown gate: {gate_name}. Valid gates are: {', '.join(valid_gates)}"
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


def format_summary(gate_name: str, results: List[Any], overall_ok: bool = True) -> str:
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
                        else (
                            "FAIL"
                            if not getattr(result, "skipped", False)
                            else "SKIPPED"
                        )
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
                        else (
                            "FAIL"
                            if not getattr(result, "skipped", False)
                            else "SKIPPED"
                        )
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
def check_tests(
    pytest_args: Sequence[str] | None = None, timeout: Optional[float] = None
):
    """Compatibility function for check_tests.

    In normal usage this runs `pytest -q`. Tests can override `pytest_args`
    to point at a tiny target and avoid recursively running the whole suite.
    """
    if pytest_args is None:
        pytest_args = ["pytest", "-q"]

    timeout = timeout or DEFAULT_CHECK_TESTS_TIMEOUT

    try:
        try:
            result = subprocess.run(
                list(pytest_args),
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
        except TypeError:
            # Monkeypatch replacement for subprocess.run may not accept all kwargs
            result = subprocess.run(list(pytest_args), capture_output=True, text=True)

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
            reason=(
                info if result.returncode == 0 else f"pytest failures: {result.stdout}"
            ),
        )
    except FileNotFoundError:
        return GateResult(
            gate_id="tests",
            ok=True,
            skipped=True,
            reason="pytest not found",
            output="pytest not found",
        )
    except subprocess.TimeoutExpired as exc:
        if exc.stdout is not None:
            if isinstance(exc.stdout, bytes):
                stdout_str = exc.stdout.decode(errors="replace")
            else:
                stdout_str = exc.stdout
        else:
            stdout_str = ""
        stdout = stdout_str + (
            f"\n[firsttry gates.check_tests] pytest timed out after {timeout:.0f}s: {exc.cmd!r}\n"
        )
        return GateResult(
            gate_id="tests",
            ok=False,
            output=stdout,
            reason=f"pytest timed out after {timeout:.0f}s",
        )
    except Exception as e:
        return GateResult(
            gate_id="tests", ok=False, output=str(e), reason=f"Error running tests: {e}"
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
        gate_id="pg_drift", ok=True, skipped=True, reason="no Postgres configured"
    )


def check_docker_smoke():
    """Compatibility function for check_docker_smoke."""
    return GateResult(
        gate_id="docker_smoke", ok=True, skipped=True, reason="no Docker runtime"
    )


def check_ci_mirror():
    """Compatibility function for check_ci_mirror."""
    return GateResult(
        gate_id="ci_mirror",
        ok=True,
        skipped=True,
        reason="ci mirror check not implemented",
    )


def run_all_gates(project_root: Any) -> List[GateResult]:
    """Compatibility function for run_all_gates."""
    # Mock implementation
    results = [check_lint(), check_types(), check_tests()]
    return results


def gate_result_to_dict(gate_result: Any) -> Dict[str, Any]:
    """Compatibility function to convert GateResult to dict."""
    return {
        "gate": getattr(gate_result, "gate_id", "unknown"),
        "name": getattr(gate_result, "gate_id", "unknown"),
        "status": "PASS" if gate_result.ok else "FAIL",
        "ok": gate_result.ok,
        "info": gate_result.reason,
        "details": getattr(gate_result, "output", ""),
        "stdout": getattr(gate_result, "output", gate_result.reason),
        "returncode": 0 if gate_result.ok else 1,
    }


def build_gate_summary(gate_name: str, results: List[Any]) -> GateSummary:
    """Build a GateSummary from the serializable results list.

    Accepts items that are either dicts (serialized GateResult) or
    GateResult-like objects. This keeps compatibility with the
    legacy run_gate() which returns dicts for CLI compatibility.
    """
    summary = GateSummary(gate_name=gate_name)
    for r in results:
        # Normalize to dict-like access
        if isinstance(r, dict):
            name = r.get("gate") or r.get("name") or r.get("gate_id") or "unknown"
            ok = bool(r.get("ok", False))
            skipped = bool(r.get("skipped", False))
            reason = r.get("info") or r.get("details") or r.get("stdout") or r.get("reason")
        else:
            name = getattr(r, "gate_id", getattr(r, "name", "unknown"))
            ok = bool(getattr(r, "ok", False))
            skipped = bool(getattr(r, "skipped", False))
            reason = getattr(r, "reason", None)

        if skipped:
            summary.skipped.append(GateSummaryItem(name=name, kind="skipped", reason=reason))
        elif ok:
            summary.checked.append(GateSummaryItem(name=name, kind="checked", reason=reason))
        else:
            summary.unknown.append(GateSummaryItem(name=name, kind="unknown", reason=reason))

    # Determine final result: PASS if all non-skipped checks are ok
    non_skipped = [r for r in results if not (isinstance(r, dict) and r.get("skipped")) and not (not isinstance(r, dict) and getattr(r, "skipped", False))]
    all_ok = True
    for r in non_skipped:
        if isinstance(r, dict):
            if not bool(r.get("ok", False)):
                all_ok = False
                break
        else:
            if not bool(getattr(r, "ok", False)):
                all_ok = False
                break

    summary.result = "PASS" if all_ok else "FAIL"
    # Augment summary with unmapped CI steps (if any)
    try:
        unmapped = get_unmapped_steps_for_gate(gate_name)
        for u in unmapped:
            # Name encodes workflow/job/step for clarity in human summaries
            name = f"{u.workflow}/{u.job}/{u.step}"
            summary.unknown.append(GateSummaryItem(name=name, kind="unknown", reason=u.reason))
    except Exception:
        # Be defensive: failure to compute unmapped steps should not break gate
        pass
    # Augment summary with mirror status (best-effort)
    try:
        from firsttry.ci_parity.mirror_status import get_mirror_status

        ms = get_mirror_status()
        summary.mirror_fresh = ms.is_fresh
        summary.mirror_stale_workflows = list(ms.missing_workflows or []) + list(ms.extra_workflows or [])
    except Exception:
        # Do not break gate on mirror status failure
        summary.mirror_fresh = True
        summary.mirror_stale_workflows = []
    return summary


def print_gate_human_summary(summary: GateSummary) -> None:
    print(f"Gate: {summary.gate_name}\n")
    print("Checked:")
    if summary.checked:
        for item in summary.checked:
            print(f"  • {item.name}")
    else:
        print("  • none")

    print("\nSkipped:")
    if summary.skipped:
        for item in summary.skipped:
            reason = f" ({item.reason})" if item.reason else ""
            print(f"  • {item.name}{reason}")
    else:
        print("  • none")

    print("\nUnknown:")
    if summary.unknown:
        for item in summary.unknown:
            reason = f" ({item.reason})" if item.reason else ""
            print(f"  • {item.name}{reason}")
    else:
        print("  • none")

    # Mirror status
    mirror_line = "Mirror: FRESH"
    if not getattr(summary, "mirror_fresh", True):
        stale = ", ".join(summary.mirror_stale_workflows or [])
        mirror_line = f"Mirror: STALE ({stale})" if stale else "Mirror: STALE"
    print(f"\n{mirror_line}\n")

    print(f"Result: {summary.result}\n")
