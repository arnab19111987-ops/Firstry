"""Coverage enforcement tool for critical modules.

Enforces minimum coverage thresholds on security-critical and core modules.
Runs after pytest to validate that coverage meets enterprise standards.

Critical modules (must reach 80%):
- src/firsttry/runner/state.py (fingerprinting)
- src/firsttry/runner/planner.py (DAG planning)
- src/firsttry/scanner.py (change detection)
- src/firsttry/smart_pytest.py (test optimization)

Usage:
    python tools/coverage_enforcer.py

Exit codes:
    0: All thresholds met
    1: One or more modules below threshold
"""

import json
import sys
from pathlib import Path
from typing import Dict, Tuple

CRITICAL = {
    "src/firsttry/runner/state.py": 80.0,
    "src/firsttry/runner/planner.py": 80.0,
    "src/firsttry/scanner.py": 80.0,
    "src/firsttry/smart_pytest.py": 80.0,
}

COVERAGE_JSON = Path(".coverage.json")
COVERAGE_DB = Path(".coverage")


def load_coverage_data() -> Dict:
    """Load coverage data from .coverage.json file."""
    try:
        if COVERAGE_JSON.exists():
            return json.loads(COVERAGE_JSON.read_text())
    except Exception as e:
        print(f"[coverage_enforcer] Warning: Could not load {COVERAGE_JSON}: {e}")
    return {}


def calculate_file_coverage(coverage_data: Dict, filepath: str) -> Tuple[float, str]:
    """Calculate coverage percentage for a file from coverage data.

    Returns:
        Tuple of (coverage_percent, status_string)
    """
    # Try to extract from coverage.json structure
    # Expected format depends on coverage.py output
    if not coverage_data:
        return 0.0, "no data"

    files = coverage_data.get("files", {})
    if filepath in files:
        file_info = files[filepath]
        summary = file_info.get("summary", {})

        num_statements = summary.get("num_statements", 0)
        num_missing = summary.get("missing_lines", 0)

        if num_statements == 0:
            return 0.0, "no statements"

        covered = num_statements - num_missing
        pct = 100.0 * covered / num_statements
        return pct, f"{covered}/{num_statements} lines"

    return 0.0, "file not in coverage data"


def use_coverage_module() -> Dict[str, float]:
    """Fallback: Use coverage module directly to compute file coverage."""
    try:
        from coverage import Coverage

        cov = Coverage(data_file=str(COVERAGE_DB))
        try:
            cov.load()
        except Exception:
            print("[coverage_enforcer] No coverage database found. Run: pytest --cov")
            return {}

        results = {}

        for filepath in CRITICAL.keys():
            try:
                # Get file analysis (executed_lines, missing_lines, etc.)
                analysis = cov.analysis2(filepath)
                if analysis:
                    # analysis returns (filename, statements, excluded, missing, branch_lines, branch_missing)
                    statements = analysis[1]  # All statement line numbers
                    missing = analysis[3]  # Missing statement line numbers

                    nstmts = len(statements)
                    nmiss = len(missing)

                    if nstmts == 0:
                        pct = 0.0
                    else:
                        pct = 100.0 * (nstmts - nmiss) / nstmts

                    results[filepath] = pct
            except Exception as e:
                print(f"[coverage_enforcer] Could not analyze {filepath}: {e}")
                results[filepath] = 0.0

        return results
    except ImportError:
        print("[coverage_enforcer] Coverage module not available")
        return {}


def main():
    """Check coverage thresholds and exit with appropriate code."""
    print("[coverage_enforcer] Checking critical module coverage thresholds...")
    print(f"[coverage_enforcer] Enforcing minimum 80% on: {list(CRITICAL.keys())}")
    print()

    # Try to load coverage data
    coverage_data = load_coverage_data()

    if not coverage_data:
        print("[coverage_enforcer] Attempting to use coverage module...")
        file_coverage = use_coverage_module()
    else:
        file_coverage = {}
        for filepath in CRITICAL.keys():
            pct, status = calculate_file_coverage(coverage_data, filepath)
            file_coverage[filepath] = pct

    if not file_coverage:
        print("[coverage_enforcer] ERROR: Could not load coverage data")
        print("             Run: pytest --cov")
        return 1

    # Check thresholds
    failures = []

    for filepath, minpct in CRITICAL.items():
        pct = file_coverage.get(filepath, 0.0)
        status = "✅ PASS" if pct >= (minpct - 1e-6) else "❌ FAIL"

        print(f"[coverage_enforcer] {status} {filepath}: {pct:.1f}% (threshold: {minpct:.0f}%)")

        if pct < (minpct - 1e-6):
            failures.append((filepath, pct, minpct))

    print()

    if failures:
        print("[coverage_enforcer] FAILURES - The following modules are below threshold:")
        print()
        for filepath, pct, minpct in failures:
            gap = minpct - pct
            print(f"  ❌ {filepath}")
            print(f"     Current:   {pct:.1f}%")
            print(f"     Required:  {minpct:.0f}%")
            print(f"     Gap:       {gap:.1f}% ({gap / minpct * 100:.0f}% relative)")
            print()

        print("[coverage_enforcer] RECOMMENDATIONS:")
        print("  1. Add unit tests for uncovered lines")
        print("  2. Use --cov-report=term-missing to identify gaps")
        print("  3. Re-run: python tools/coverage_enforcer.py")
        print()
        return 1
    else:
        print("[coverage_enforcer] ✅ SUCCESS - All critical modules meet thresholds!")
        print(f"[coverage_enforcer] Enforced coverage on {len(CRITICAL)} modules")
        return 0


if __name__ == "__main__":
    sys.exit(main())
