#!/usr/bin/env python3
import argparse
import csv
import json
import os
from pathlib import Path
from statistics import median, mean, pstdev
from datetime import datetime


def load_jsonl(p: Path):
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except Exception:
            continue


def group_key(row):
    return (row.get("scenario"), row.get("run_mode") or row.get("run_mode") or row.get("mode"), row.get("toolchain"))


def agg_rows(rows):
    ws = [r.get("wall_seconds") for r in rows if isinstance(r.get("wall_seconds"), (int, float))]
    if not ws:
        return {"n": 0}
    ssorted = sorted(ws)
    n = len(ssorted)
    d = {
        "n": n,
        "median": round(median(ssorted), 3),
        "p10": round(ssorted[max(0, (n * 1) // 10)], 3) if n >= 10 else round(min(ssorted), 3),
        "p90": round(ssorted[min(n - 1, (n * 9) // 10)], 3) if n >= 10 else round(max(ssorted), 3),
        "mean": round(mean(ssorted), 3),
        "stddev": round(pstdev(ssorted), 3) if n > 1 else 0.0,
        "best": round(min(ssorted), 3),
    }
    return d


def main():
    ap = argparse.ArgumentParser(description="Aggregate FirstTry vs Manual bench results.")
    ap.add_argument("--raw-dir", default=os.environ.get("RAW_DIR", ".firsttry/bench/raw"),
                    help="Directory containing *.jsonl raw rows")
    ap.add_argument("--out-dir", default=os.environ.get("OUT_DIR", ".firsttry/bench"),
                    help="Directory to write report.md and summary.csv")
    ap.add_argument("-V", "--verbose", action="store_true")
    args = ap.parse_args()

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    if raw_dir.exists():
        for p in sorted(raw_dir.glob("*.jsonl")):
            if args.verbose:
                print(f"[aggregate] reading {p}")
            rows.extend(list(load_jsonl(p)))

    groups = {}
    for r in rows:
        groups.setdefault(group_key(r), []).append(r)

    agg = {}
    for k, rs in groups.items():
        agg[k] = agg_rows(rs)

    # build comparison tuples (ft vs manual)
    by_scen_mode = {}
    for (scenario, mode, toolchain), stats in agg.items():
        by_scen_mode.setdefault((scenario, mode), {})[toolchain or ""] = stats

    csv_path = out_dir / "summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "mode", "ft_n", "ft_median", "manual_n", "manual_median", "delta(manual-ft)", "speedup(manual/ft)"])
        for (scenario, mode), d in sorted(by_scen_mode.items()):
            ft = d.get("ft", {})
            man = d.get("manual", {})
            ft_med = ft.get("median")
            man_med = man.get("median")
            delta = (man_med - ft_med) if (ft_med is not None and man_med is not None) else ""
            speed = (round(man_med / ft_med, 3) if (ft_med and man_med and ft_med > 0) else "")
            w.writerow([scenario, mode, ft.get("n", 0), ft_med, man.get("n", 0), man_med, delta, speed])

    md = []
    md.append(f"# FirstTry Bench Report\n")
    md.append(f"_Generated: {datetime.utcnow().isoformat()}Z_\n")
    md.append("\n| Scenario | Mode | FT median (s) | Manual median (s) | Δ (manual−ft) | Speedup (×) |\n|---:|:---:|---:|---:|---:|---:|")
    for (scenario, mode), d in sorted(by_scen_mode.items()):
        ft = d.get("ft", {})
        man = d.get("manual", {})
        ft_med = ft.get("median", "")
        man_med = man.get("median", "")
        delta = (man_med - ft_med) if (ft_med and man_med) else ""
        speed = (round(man_med / ft_med, 2) if (ft_med and man_med and ft_med > 0) else "")
        md.append(f"| {scenario} | {mode} | {ft_med} | {man_med} | {delta} | {speed} |")

    (out_dir / "report.md").write_text("\n".join(md), encoding="utf-8")
    if args.verbose:
        print(f"Wrote: {csv_path}")
        print(f"Wrote: {out_dir / 'report.md'}")


if __name__ == "__main__":
    main()
