from __future__ import annotations

import csv
from pathlib import Path


def main() -> None:
    manual_dir = Path(".firsttry/bench/manual")
    if not manual_dir.exists():
        raise SystemExit("No .firsttry/bench/manual directory found")

    # Pick latest benchmark
    runs = sorted([p for p in manual_dir.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True)
    if not runs:
        raise SystemExit("No benchmark runs found in .firsttry/bench/manual")
    latest = runs[0]
    matrix = latest / "bench_matrix.tsv"
    if not matrix.exists():
        raise SystemExit(f"No bench_matrix.tsv in {latest}")

    print(f"Using latest benchmark: {latest}")
    rows = list(csv.DictReader(matrix.open("r", encoding="utf-8"), delimiter="\t"))

    for row in rows:
        print(
            f"{row['label']:16s} {row['kind']:10s}"
            f" time={row['seconds']:>8s}s"
            f" rc={row['exit_code']}"
        )

    print("\nSanity checks:")
    failures = [r for r in rows if r['exit_code'] != '0']
    if failures:
        print("  ❌ Some cases failed:")
        for r in failures:
            print(f"    - {r['label']} ({r['kind']}): rc={r['exit_code']}")
    else:
        print("  ✅ All cases rc=0")


if __name__ == "__main__":
    main()
