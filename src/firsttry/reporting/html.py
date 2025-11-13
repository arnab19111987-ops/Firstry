from __future__ import annotations

import argparse
import datetime as dt
import html as html_module
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

# ------------- LEGACY: Backward compatibility functions --------


def write_html_report(repo_root: Path, results: dict, out: str = ".firsttry/report.html") -> None:
    """Legacy function: write simple HTML report for task results."""
    rows = []
    for tid, r in results.items():
        # prefer explicit cache_status; otherwise use is_cache_hit when available
        cache = getattr(r, "cache_status", None)
        if cache is None:
            # If object exposes is_cache_hit, use that to indicate a local hit.
            if getattr(r, "is_cache_hit", False):
                # try to preserve remote hint if present on status
                cache = "hit-remote" if getattr(r, "status", "") == "hit-remote" else "hit-local"
            else:
                cache = "miss-run"
        status = getattr(r, "status", "")
        rows.append(
            f"<tr><td>{html_module.escape(tid)}</td><td>{html_module.escape(status)}</td><td>{getattr(r, 'duration_ms', 0)}</td><td>{cache}</td></tr>",
        )
    html_doc = f"""<!doctype html><meta charset="utf-8">
    <title>FirstTry Report</title>
    <style>body{{font:14px system-ui}}td,th{{border:1px solid #ddd;padding:6px}}table{{border-collapse:collapse}}</style>
    <h2>FirstTry Report — {time.strftime('%Y-%m-%d %H:%M:%S')}</h2>
    <table><thead><tr><th>Task</th><th>Status</th><th>Duration (ms)</th><th>Cache</th></tr></thead>
    <tbody>{''.join(rows)}</tbody></table>"""
    p = repo_root / out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html_doc)


def write_html_dashboard(repo_root: Path, out: str = ".firsttry/dashboard.html") -> None:
    """Legacy function: write simple HTML dashboard aggregating all reports."""
    rpt_dir = repo_root / ".firsttry"
    reports = []
    for p in sorted(rpt_dir.glob("*.json")):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            if not text.strip():
                continue
            data = json.loads(text)
        except Exception:
            continue
        reports.append((p.name, p.stat().st_mtime, data))

    if not reports:
        (repo_root / out).write_text("<html><body><h3>No reports found.</h3></body></html>")
        return

    total_hits = total_runs = total_saved = 0
    top_fail: Dict[str, int] = {}
    flaky: Dict[str, int] = {}
    prev: Dict[str, int] = {}

    rows = []
    for name, ts, data in reports:
        checks = data.get("checks", {})
        hits = sum(
            1 for c in checks.values() if c.get("cache_status") in {"hit-local", "hit-remote"}
        )
        runs = sum(1 for c in checks.values() if c.get("cache_status", "miss-run") == "miss-run")
        saved = sum(
            int(c.get("duration_ms", 0))
            for c in checks.values()
            if c.get("cache_status") in {"hit-local", "hit-remote"}
        )
        total_hits += hits
        total_runs += runs
        total_saved += saved
        rows.append(
            f"<tr><td>{html_module.escape(name)}</td><td>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))}</td><td>{hits}</td><td>{runs}</td><td>{saved}</td></tr>",
        )

        for k, c in checks.items():
            st = c.get("status", "")
            if st != "ok":
                top_fail[k] = top_fail.get(k, 0) + 1
            if k in prev and ((prev[k] == "ok") ^ (st == "ok")):
                flaky[k] = flaky.get(k, 0) + 1
            prev[k] = st

    def _ol(d: Dict[str, int]) -> str:
        if not d:
            return "<i>None</i>"
        items = "".join(
            f"<li>{html_module.escape(k)} — {v}</li>"
            for k, v in sorted(d.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        return f"<ol>{items}</ol>"

    html_doc = f"""<!doctype html><meta charset="utf-8">
    <title>FirstTry Dashboard</title>
    <style>body{{font:14px system-ui}}td,th{{border:1px solid #ddd;padding:6px}}table{{border-collapse:collapse}}</style>
    <h2>FirstTry ROI Dashboard</h2>
    <p><b>Total cache hits:</b> {total_hits} &nbsp; <b>Total local runs:</b> {total_runs} &nbsp; <b>Estimated time saved:</b> {total_saved / 1000:.2f}s</p>
    <h3>Run History</h3>
    <table><thead><tr><th>Report</th><th>When</th><th>Cache Hits</th><th>Local Runs</th><th>Saved (ms)</th></tr></thead>
    <tbody>{''.join(rows)}</tbody></table>
    <h3>Top Failing Checks</h3>{_ol(top_fail)}
    <h3>Most Flaky Checks</h3>{_ol(flaky)}"""
    (repo_root / out).write_text(html_doc)


# ------------- 1) Data Loading ----------------


def _parse_timestamp(ts: Any, fallback_epoch: float) -> dt.datetime:
    """
    Accepts:
      - ISO 8601 string (e.g., "2025-11-07T09:20:56.78Z" or without Z)
      - float/int epoch seconds
      - None -> fallback to file mtime
    Returns timezone-naive UTC-ish datetime for chart bucketing.
    """
    if ts is None:
        return dt.datetime.fromtimestamp(fallback_epoch)
    if isinstance(ts, (int, float)):
        return dt.datetime.fromtimestamp(float(ts))
    if isinstance(ts, str):
        s = ts.strip().rstrip("Z")
        try:
            return dt.datetime.fromisoformat(s)
        except Exception:
            # try common alt format
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
                try:
                    return dt.datetime.strptime(s, fmt)
                except Exception:
                    pass
    # fallback
    return dt.datetime.fromtimestamp(fallback_epoch)


def load_all_reports(report_dir: Path) -> List[Dict]:
    """
    Finds all report*.json files (non-recursive), loads them, sorts oldest->newest.
    Expected report schema (minimum used here):
      - run_timestamp: ISO string or epoch (optional)
      - tasks: [ { id, status, duration_ms, cache }, ... ]
      - run_summary: { total_duration_ms, ... } (optional)
    """
    reports: List[Tuple[dt.datetime, Dict]] = []
    for p in sorted(report_dir.glob("report*.json")):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            if not text.strip():
                continue
            data = json.loads(text)
        except Exception:
            continue
        ts = _parse_timestamp(data.get("run_timestamp"), p.stat().st_mtime)
        reports.append((ts, data))
    reports.sort(key=lambda x: x[0])
    return [d for _, d in reports]


# ------------- 2) Aggregations ----------------


def analyze_cache_savings(reports: List[Dict]) -> Dict[str, int]:
    """
    Date -> total milliseconds 'saved' by cache hits that day.
    Uses task.cache == 'hit-local' (or 'hit-remote' if you have it).
    """
    per_day: Dict[str, int] = defaultdict(int)
    for r in reports:
        ts = _parse_timestamp(r.get("run_timestamp"), fallback_epoch=0)
        day = ts.strftime("%Y-%m-%d")
        saved = 0
        for t in r.get("tasks", []):
            cache_val = (t.get("cache") or t.get("cache_status") or "").lower()
            if cache_val in ("hit-local", "hit-remote"):
                saved += int(t.get("duration_ms", 0))
        per_day[day] += saved
    return dict(sorted(per_day.items()))


def analyze_top_failures(reports: List[Dict], top_n: int = 10) -> Dict[str, int]:
    """
    Task ID -> failure count (top N).
    """
    counter: Counter = Counter()
    for r in reports:
        for t in r.get("tasks", []):
            if (t.get("status") or "").lower() == "fail":
                counter[t.get("id", "unknown")] += 1
    return dict(counter.most_common(top_n))


def analyze_flakiness(reports: List[Dict]) -> Dict[str, int]:
    """
    Task IDs that have both ok and fail across all runs -> 1 (boolean signal).
    """
    seen: Dict[str, set] = defaultdict(set)
    for r in reports:
        for t in r.get("tasks", []):
            tid = t.get("id", "unknown")
            seen[tid].add((t.get("status") or "").lower())
    flaky = {tid: 1 for tid, outcomes in seen.items() if "ok" in outcomes and "fail" in outcomes}
    return flaky


def compute_kpis(reports: List[Dict]) -> Dict[str, Any]:
    """
    High-level KPIs for the top of the dashboard.
    - total_runs
    - pass_rate (by run: run passes if all tasks ok)
    - cache_hit_ratio (by task)
    - total_time_saved_ms (by task)
    - avg_run_time_ms (if run_summary.total_duration_ms present, else sum of tasks)
    """
    total_runs = len(reports)
    if total_runs == 0:
        return {
            "total_runs": 0,
            "pass_rate": 0.0,
            "cache_hit_ratio": 0.0,
            "total_time_saved_ms": 0,
            "avg_run_time_ms": 0,
        }

    run_passes = 0
    total_task_count = 0
    cache_hits = 0
    total_time_saved = 0
    total_runtime = 0

    for r in reports:
        tasks = r.get("tasks", [])
        total_task_count += len(tasks)
        if tasks and all((t.get("status") or "").lower() == "ok" for t in tasks):
            run_passes += 1

        for t in tasks:
            cache_val = (t.get("cache") or t.get("cache_status") or "").lower()
            if cache_val in ("hit-local", "hit-remote"):
                cache_hits += 1
                total_time_saved += int(t.get("duration_ms", 0))

        # Prefer explicit run duration if provided
        rs = r.get("run_summary") or {}
        rd = rs.get("total_duration_ms")
        if isinstance(rd, (int, float)):
            total_runtime += int(rd)
        else:
            total_runtime += sum(int(t.get("duration_ms", 0)) for t in tasks)

    pass_rate = (run_passes / total_runs) * 100.0
    cache_hit_ratio = (cache_hits / total_task_count * 100.0) if total_task_count else 0.0
    avg_run_time = int(total_runtime / total_runs) if total_runs else 0

    return {
        "total_runs": total_runs,
        "pass_rate": round(pass_rate, 1),
        "cache_hit_ratio": round(cache_hit_ratio, 1),
        "total_time_saved_ms": int(total_time_saved),
        "avg_run_time_ms": int(avg_run_time),
    }


# ------------- 3) HTML Emit -------------------

_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>FirstTry ROI Dashboard</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root { --fg:#0b0b0b; --muted:#666; --accent:#0ea5e9; }
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; color: var(--fg); margin: 24px; }
    h1 { margin-bottom: 8px; }
    .kpis { display:flex; gap:16px; flex-wrap:wrap; margin: 12px 0 28px; }
    .kpi { border:1px solid #eee; border-radius:10px; padding:12px 16px; min-width: 180px; }
    .kpi .label { font-size:12px; color:var(--muted); }
    .kpi .value { font-size:22px; font-weight:600; }
    .chart { width:min(1100px, 95vw); margin: 0 0 48px 0; }
    footer { margin-top:40px; color:var(--muted); font-size:12px; }
    code { background:#fafafa; padding:2px 6px; border-radius:6px; }
  </style>
</head>
<body>
  <h1>FirstTry ROI Dashboard</h1>
  <p class="muted">Aggregated performance across all runs in this workspace.</p>

  <div class="kpis" id="kpis"></div>

  <h2>Time Saved by Cache (per day)</h2>
  <div class="chart"><canvas id="cacheChart"></canvas></div>

  <h2>Top Failing Checks</h2>
  <div class="chart"><canvas id="failChart"></canvas></div>

  <h2>Flaky Tasks (flip-flopped between pass & fail)</h2>
  <p id="flakyList"></p>

  <script id="data" type="application/json">{DATA}</script>
  <script>
    const data = JSON.parse(document.getElementById('data').textContent);

    // KPIs
    const k = data.kpis;
    const kpi = (label, value) => `
      <div class="kpi">
        <div class="label">${label}</div>
        <div class="value">${value}</div>
      </div>`;
    document.getElementById('kpis').innerHTML =
      kpi("Total Runs", k.total_runs) +
      kpi("Pass Rate", k.pass_rate + "%") +
      kpi("Cache Hit Ratio", k.cache_hit_ratio + "%") +
      kpi("Total Time Saved", (k.total_time_saved_ms/1000).toFixed(1) + " s") +
      kpi("Avg Run Time", (k.avg_run_time_ms/1000).toFixed(1) + " s");

    // Cache chart
    const cacheLabels = Object.keys(data.cache_savings);
    const cacheValues = cacheLabels.map(d => data.cache_savings[d]);
    new Chart(document.getElementById('cacheChart'), {
      type: 'line',
      data: {
        labels: cacheLabels,
        datasets: [{
          label: 'Time Saved (ms)',
          data: cacheValues,
          tension: 0.2,
          borderColor: 'rgb(14,165,233)',
          fill: false
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: true } },
        scales: { x: { ticks: { autoSkip: true, maxTicksLimit: 12 } } }
      }
    });

    // Failures bar
    const failLabels = Object.keys(data.top_failures);
    const failValues = failLabels.map(k => data.top_failures[k]);
    new Chart(document.getElementById('failChart'), {
      type: 'bar',
      data: {
        labels: failLabels,
        datasets: [{
          label: '# of Failures',
          data: failValues,
          backgroundColor: 'rgba(239, 68, 68, 0.25)',
          borderColor: 'rgba(239, 68, 68, 1.0)',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        indexAxis: 'y',
        plugins: { legend: { display: true } }
      }
    });

    // Flaky list
    const flaky = Object.keys(data.flaky_tasks);
    document.getElementById('flakyList').innerHTML =
      flaky.length ? ("<ul>" + flaky.map(t => "<li><code>"+t+"</code></li>").join("") + "</ul>")
                   : "<em>No flaky tasks detected across analyzed runs.</em>";
  </script>

  <footer>
    <p>Generated by FirstTry ROI Dashboard. Source: aggregated report JSON files in <code>.firsttry/</code>.</p>
  </footer>
</body>
</html>
"""


# ------------- 4) Main: glue & CLI ---------------


def generate_dashboard(report_dir: Path, output_html: Path) -> None:
    all_reports = load_all_reports(report_dir)
    if not all_reports:
        output_html.write_text(
            "<html><body><h1>No reports found.</h1></body></html>",
            encoding="utf-8",
        )
        return

    data = {
        "kpis": compute_kpis(all_reports),
        "cache_savings": analyze_cache_savings(all_reports),
        "top_failures": analyze_top_failures(all_reports),
        "flaky_tasks": analyze_flakiness(all_reports),
        "total_runs": len(all_reports),
    }
    html = _HTML.replace("{DATA}", json.dumps(data, ensure_ascii=False))
    output_html.write_text(html, encoding="utf-8")


def _cli() -> None:
    ap = argparse.ArgumentParser(description="FirstTry ROI Dashboard (aggregate reports → HTML)")
    ap.add_argument("report_dir", help="Directory containing report*.json (e.g., .firsttry/)")
    ap.add_argument(
        "--out",
        dest="out",
        default="firsttry_roi_dashboard.html",
        help="Output HTML path (default: firsttry_roi_dashboard.html)",
    )
    args = ap.parse_args()

    rd = Path(args.report_dir).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"[FirstTry] Aggregating reports from: {rd}")
    generate_dashboard(rd, out)
    print(f"[FirstTry] Dashboard saved to: {out}")


if __name__ == "__main__":
    _cli()
