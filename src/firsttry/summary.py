# src/firsttry/summary.py

from typing import List, Optional

# optional: keep consistent ordering
GATE_ORDER = [
    "python-lint",
    "python-format",
    "python-imports",
    "python-type",
    "pytest",
    "security",
    "js-lint",
    "dup",
    "maintainability",
    "hooks",
]


def print_run_summary(
    results: List, elapsed: float, *, missing_cmds: Optional[list[str]] = None
):
    """
    results: list of objects/dicts with at least:
      - name/gate (str)
      - passed/ok (bool)
      - errors (int, optional)
      - fixable (int, optional)
      - mode ("auto" | "detect" | "advisory"), optional
      - extra (dict), optional
    """
    total = len(results)

    # Helper function to get values from either dict or object
    def get_value(item, key, default=None, alt_key=None):
        if isinstance(item, dict):
            return item.get(key, item.get(alt_key, default) if alt_key else default)
        else:
            return getattr(
                item, key, getattr(item, alt_key, default) if alt_key else default
            )

    failed = [r for r in results if not get_value(r, "passed", False, "ok")]

    if not failed:
        print(f"✅ All checks passed ({total} gates) in {elapsed:.1f}s\n")
    else:
        print(f"❌ Checks failed ({len(failed)}/{total} gates) in {elapsed:.1f}s\n")

    # sort
    order_map = {name: i for i, name in enumerate(GATE_ORDER)}

    def _sort_key(r):
        name = get_value(r, "name", "zzz", "gate")
        return order_map.get(name, 999)

    results_sorted = sorted(results, key=_sort_key)

    print("Gates:")
    for r in results_sorted:
        name = get_value(r, "name", "unknown", "gate")
        passed = get_value(r, "passed", False, "ok")
        errors = get_value(r, "errors", 0) or 0
        fixable = get_value(r, "fixable", 0) or 0
        mode = get_value(r, "mode", None)
        extra = get_value(r, "extra", {}) or {}

        line = f"  • {name.ljust(16)}"
        if passed:
            line += "✅"
        else:
            line += "❌"
            parts = []
            if errors:
                parts.append(f"{errors} errors")
            if fixable:
                parts.append(f"({fixable} fixable)")
            if mode in ("detect", "advisory"):
                parts.append("[manual]")
            # pytest special-case
            if name in ("pytest", "tests"):
                first_fail = extra.get("first_failed_test")
                if first_fail:
                    parts.append(first_fail)
            if parts:
                line += " " + " ".join(parts)
        print(line)

    # show missing deps
    if missing_cmds:
        print("\n👉 Install missing tools:")
        for cmd in missing_cmds:
            print(f"   - {cmd}")

    # final hint
    if failed:
        # if any fixable gate failed
        if any(getattr(r, "fixable", 0) for r in failed):
            print("\n👉 Run: firsttry run --gate pre-commit --autofix")
        else:
            print("\n👉 Some checks require manual fixes (types/tests/security).")
    else:
        print("\n🎉 Ready to commit & push.")
