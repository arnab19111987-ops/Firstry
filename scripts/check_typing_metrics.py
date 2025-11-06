#!/usr/bin/env python3
"""Check typing crutches against baseline - prevents regression."""

import sys
from pathlib import Path


def parse_baseline(baseline_file: str) -> dict[str, int]:
    """Parse baseline file (format: crutch=count)."""
    baseline = {}
    try:
        with open(baseline_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("=")
                if len(parts) == 2:
                    baseline[parts[0]] = int(parts[1])
    except FileNotFoundError:
        print(f"❌ Baseline file not found: {baseline_file}")
        sys.exit(1)
    return baseline


def parse_current(current_file: str) -> dict[str, int]:
    """Parse current counts file (same format as baseline)."""
    return parse_baseline(current_file)  # reuse parsing logic


def main():
    """Check current typing metrics against baseline."""
    baseline_file = ".quality/typing_baseline.txt"
    current_file = ".quality/typing_current.txt"

    # Regenerate current counts
    import subprocess

    result = subprocess.run(
        ["python", "scripts/count_typing_crutches.py"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print(f"❌ Error counting typing crutches: {result.stderr}")
        sys.exit(1)

    # Write current counts to temp file
    Path(".quality").mkdir(exist_ok=True)
    with open(current_file, "w") as f:
        f.write(result.stdout)

    baseline = parse_baseline(baseline_file)
    current = parse_current(current_file)

    # Check for regressions (increases)
    regressions = []
    for crutch in baseline.keys():
        baseline_count = baseline[crutch]
        current_count = current.get(crutch, 0)
        if current_count > baseline_count:
            regressions.append(
                f"  {crutch}: {baseline_count} → {current_count} (+{current_count - baseline_count})",
            )

    if regressions:
        print("❌ Typing metric regression detected:")
        for reg in regressions:
            print(reg)
        sys.exit(1)
    else:
        # Show improvement or no change
        print("✅ Typing metrics OK")
        for crutch in baseline.keys():
            baseline_count = baseline[crutch]
            current_count = current.get(crutch, 0)
            if current_count < baseline_count:
                print(
                    f"  ✨ {crutch}: {baseline_count} → {current_count} (-{baseline_count - current_count})",
                )
            else:
                print(f"  → {crutch}: {current_count}")


if __name__ == "__main__":
    main()
