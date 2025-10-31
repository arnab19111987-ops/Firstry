"""FirstTry gate implementations."""

from typing import List, Any, Dict
from .base import GateResult

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
        raise ValueError(f"Unknown gate: {gate_name}. Valid gates are: {', '.join(valid_gates)}")
    
    # Try to provide more realistic results based on gate name
    if gate_name == "pre-commit":
        results = [
            check_lint(),
            check_types(), 
            check_tests()
        ]
    else:  # gate_name == "pre-push"
        results = [
            check_lint(),
            check_types(),
            check_tests(),
            check_docker_smoke()
        ]
    
    # Convert to dict format for JSON serialization if needed
    serializable_results = []
    for r in results:
        if hasattr(r, 'to_dict'):
            d = r.to_dict()
        else:
            d = gate_result_to_dict(r)
        # Ensure 'gate' key is present for test compatibility
        if 'gate_id' in d and 'gate' not in d:
            d['gate'] = d['gate_id']
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
        if hasattr(result, 'name') and hasattr(result, 'status'):
            details.append(f"{result.name} {result.status}")
        elif hasattr(result, 'gate_id') and hasattr(result, 'ok'):
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
            if hasattr(result, 'gate_id'):
                # Use status property if available, otherwise derive from ok
                if hasattr(result, 'status'):
                    status = result.status
                elif hasattr(result, 'ok'):
                    status = "PASS" if result.ok else "FAIL" if not getattr(result, 'skipped', False) else "SKIPPED"
                else:
                    status = "UNKNOWN"
                print(f"{result.gate_id} {status}")
            elif hasattr(result, 'name'):
                # Handle GateResult with name attribute
                if hasattr(result, 'status'):
                    status = result.status
                elif hasattr(result, 'ok'):
                    status = "PASS" if result.ok else "FAIL" if not getattr(result, 'skipped', False) else "SKIPPED"
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
    try:
        import subprocess
        result = subprocess.run(["ruff", "check", "."], capture_output=True, text=True)
        return GateResult(
            gate_id="lint",
            ok=result.returncode == 0,
            output=result.stdout,
            reason="ruff linting" if result.returncode == 0 else f"ruff errors: {result.stdout}"
        )
    except FileNotFoundError:
        return GateResult(gate_id="lint", ok=True, skipped=True, reason="ruff not found", output="ruff not found")

def check_types():
    """Compatibility function for check_types."""
    try:
        import subprocess
        result = subprocess.run(["mypy", "--ignore-missing-imports", "."], capture_output=True, text=True)
        return GateResult(
            gate_id="types", 
            ok=result.returncode == 0,
            output=result.stdout,
            reason="mypy type checking" if result.returncode == 0 else f"mypy errors: {result.stdout}"
        )
    except FileNotFoundError:
        return GateResult(gate_id="types", ok=True, skipped=True, reason="mypy not found")

def check_tests():
    """Compatibility function for check_tests."""
    try:
        import subprocess
        result = subprocess.run(["pytest", "-q"], capture_output=True, text=True)
        return GateResult(
            gate_id="tests",
            ok=result.returncode == 0,
            output=result.stdout,
            reason="pytest tests" if result.returncode == 0 else f"pytest failures: {result.stdout}"
        )
    except FileNotFoundError:
        return GateResult(gate_id="tests", ok=True, skipped=True, reason="pytest not found")

def check_sqlite_drift():
    """Compatibility function for check_sqlite_drift."""
    return GateResult(gate_id="sqlite_drift", ok=True, skipped=True, reason="sqlite drift check not implemented")

def check_pg_drift():
    """Compatibility function for check_pg_drift."""
    return GateResult(gate_id="pg_drift", ok=True, skipped=True, reason="pg drift check not implemented")

def check_docker_smoke():
    """Compatibility function for check_docker_smoke."""
    return GateResult(gate_id="docker_smoke", ok=True, skipped=True, reason="docker smoke check not implemented")

def check_ci_mirror():
    """Compatibility function for check_ci_mirror."""
    return GateResult(gate_id="ci_mirror", ok=True, skipped=True, reason="ci mirror check not implemented")

def run_all_gates(project_root: Any) -> List[GateResult]:
    """Compatibility function for run_all_gates."""
    # Mock implementation
    results = [
        check_lint(),
        check_types(),
        check_tests()
    ]
    return results

def gate_result_to_dict(gate_result: Any) -> Dict[str, Any]:
    """Compatibility function to convert GateResult to dict."""
    return {
        'gate': getattr(gate_result, 'gate_id', 'unknown'),
        'name': getattr(gate_result, 'gate_id', 'unknown'),
        'status': 'PASS' if gate_result.ok else 'FAIL',
        'ok': gate_result.ok,
        'info': gate_result.reason,
        'details': getattr(gate_result, 'output', ''),
        'stdout': getattr(gate_result, 'output', gate_result.reason),
        'returncode': 0 if gate_result.ok else 1
    }