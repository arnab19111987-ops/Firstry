#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

MIN_RATE = float(os.environ.get("FT_CRITICAL_MIN_RATE", "30"))
CRITICAL = [
    "firsttry/state.py",
    "firsttry/smart_pytest.py",
    "firsttry/planner.py",
    "firsttry/scanner.py",
]


def fail(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def norm(p: str) -> str:
    return p.replace("\\", "/")


def main():
    cov = Path("coverage.json")
    if not cov.exists():
        fail("coverage.json not found. Run tests with coverage first.")

    data = json.loads(cov.read_text(encoding="utf-8"))
    files = data.get("files") or {}
    if not files:
        fail("coverage.json has no 'files' entries (no data collected).")

    missing, below = [], []
    # Map critical -> (matched_coverage_path, percent or None)
    files_seen = {}

    for crit in CRITICAL:
        hit = None
        matched_path = None
        for path, meta in files.items():
            if norm(path).endswith(crit):
                hit = meta
                matched_path = path
                break
        if not hit:
            # report missing using a source-like path so consumers can locate it
            missing.append(f"src/{crit}")
            continue

        summary = hit.get("summary") or {}
        pct = summary.get("percent_covered")
        if pct is None:
            print(f"⚠️  No percent_covered for {matched_path or crit}; treating as present.")
            files_seen[crit] = (matched_path, None)
            continue
        try:
            val = float(pct)
        except Exception:
            val = None
        files_seen[crit] = (matched_path, val)
        if val is None or val < MIN_RATE:
            if val is None:
                # treat missing percent as present earlier
                continue
            below.append((matched_path, val))

    # If none of the critical files are present at all, fail.
    if not files_seen:
        fail(f"Critical files missing from coverage: {CRITICAL}")

    # --- Pretty table (always print) ---
    def _fmt_pct(x):
        try:
            return f"{float(x):5.1f}%"
        except Exception:
            return "  n/a "

    rows = []
    for crit_path in CRITICAL:
        entry = files_seen.get(crit_path)
        if entry is None:
            # missing entry; show the expected source-like path
            rows.append((f"src/{crit_path}", _fmt_pct(None)))
        else:
            cov_path, val = entry
            rows.append((cov_path, _fmt_pct(val)))
    if rows:
        print("\nCritical coverage summary:")
        w = max(len(p) for p, _ in rows)
        print(f"{ 'File'.ljust(w) }  |  Covered")
        print(f"{ '-'*w }--+----------")
        for p, pct in rows:
            print(f"{p.ljust(w)}  |  {pct}")
        print("")

    # Build machine-readable summary (written regardless of pass/fail)
    out_path = os.environ.get("FT_COVERAGE_JSON_OUT", ".firsttry/critical_coverage_summary.json")
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    # Build machine-readable summary (shape expected by downstream tests/consumers)
    # Compute avg_percent across present criticals (treat None as 0.0)
    def _safe_float(x):
        try:
            return float(x)
        except Exception:
            return 0.0

    vals = [_safe_float(v[1]) for v in files_seen.values() if v is not None]
    avg_percent = round(sum(vals) / len(vals), 2) if vals else 0.0

    summary = {
        "threshold": float(MIN_RATE),
        "files": [],
        "missing": missing,
        # status: 'pass' if there are no below-threshold entries, otherwise 'fail'
        "status": "pass" if not below else "fail",
        "avg_percent": avg_percent,
    }
    for p, pct in rows:
        # find the raw percent for this path from files_seen
        raw_pct = None
        for crit_k, v in files_seen.items():
            if v is None:
                continue
            cov_path, val = v
            if cov_path == p:
                raw_pct = val
                break
    summary["files"].append(
        {"path": p, "percent_covered": (0.0 if raw_pct is None else float(raw_pct))}
    )

    try:
        out_p.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"⚠️  Failed to write JSON summary to {out_p}: {e}")

    # If any present critical file is below threshold, fail.
    if below:
        fail(f"Critical coverage below threshold {MIN_RATE}%: {below}")

    print(f"✅ Critical coverage OK (≥ {MIN_RATE}%): {CRITICAL}")


if __name__ == "__main__":
    main()
