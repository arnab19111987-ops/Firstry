# src/firsttry/reporting/__init__.py
"""FirstTry reporting modules."""

# Public, circular-safe re-exports
from ..compat_shims import print_report  # noqa: F401
from ..compat_shims import write_report_async  # noqa: F401
from ..gates.base import GateResult
from .renderer import write_json

# Re-export from local modules
from .tty import render_tty

__all__ = ["print_summary", "render_tty", "write_json", "print_report", "write_report_async"]


def print_summary(results: list[GateResult]) -> None:
    """Print a summary of gate results (re-exported for backward compatibility)."""
    print("\n=== FirstTry Summary ===")
    ok_count = 0
    skip_count = 0
    fail_count = 0

    for r in results:
        if r.skipped:
            status = "[SKIP]"
            skip_count += 1
        elif r.ok:
            status = "[ OK ]"
            ok_count += 1
        else:
            status = "[FAIL]"
            fail_count += 1
        print(f"{status} {r.gate_id}")
        if r.reason and r.skipped:
            print(f"       reason: {r.reason}")
        if not r.ok and r.output:
            print("------- output -------")
            print(r.output.strip())
            print("----------------------")

    print(f"\nOK: {ok_count}  Skipped: {skip_count}  Failed: {fail_count}")
