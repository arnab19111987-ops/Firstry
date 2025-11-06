from __future__ import annotations
from pathlib import Path
import json
import html
import time


def _load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def write_html_report(repo_root: Path, results: dict, out: str = ".firsttry/report.html") -> None:
    rows = []
    for tid, r in results.items():
        # prefer explicit cache_status; otherwise use is_cache_hit when available
        cache = getattr(r, 'cache_status', None)
        if cache is None:
            # If object exposes is_cache_hit, use that to indicate a local hit.
            if getattr(r, 'is_cache_hit', False):
                # try to preserve remote hint if present on status
                cache = "hit-remote" if getattr(r, 'status', '') == 'hit-remote' else "hit-local"
            else:
                cache = "miss-run"
        status = getattr(r, 'status', '')
        rows.append(f"<tr><td>{html.escape(tid)}</td><td>{html.escape(status)}</td><td>{getattr(r,'duration_ms',0)}</td><td>{cache}</td></tr>")
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
    rpt_dir = repo_root / ".firsttry"
    reports = []
    for p in sorted(rpt_dir.glob("*.json")):
        data = _load_json(p)
        reports.append((p.name, p.stat().st_mtime, data))
    if not reports:
        (repo_root / out).write_text("<html><body><h3>No reports found.</h3></body></html>")
        return

    total_hits = total_runs = total_saved = 0
    top_fail = {}
    flaky = {}
    prev = {}

    rows = []
    for name, ts, data in reports:
        checks = data.get("checks", {})
        hits = sum(1 for c in checks.values() if c.get("cache_status") in {"hit-local","hit-remote"})
        runs = sum(1 for c in checks.values() if c.get("cache_status","miss-run") == "miss-run")
        saved = sum(int(c.get("duration_ms",0)) for c in checks.values() if c.get("cache_status") in {"hit-local","hit-remote"})
        total_hits += hits
        total_runs += runs
        total_saved += saved
        rows.append(
            f"<tr><td>{html.escape(name)}</td><td>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))}</td><td>{hits}</td><td>{runs}</td><td>{saved}</td></tr>"
        )

        for k, c in checks.items():
            st = c.get("status","")
            if st != "ok":
                top_fail[k] = top_fail.get(k,0) + 1
            if k in prev and ((prev[k]=="ok") ^ (st=="ok")):
                flaky[k] = flaky.get(k,0) + 1
            prev[k] = st

    def _ol(d):
        if not d:
            return "<i>None</i>"
        items = "".join(
            f"<li>{html.escape(k)} — {v}</li>"
            for k, v in sorted(d.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        return f"<ol>{items}</ol>"

    html_doc = f"""<!doctype html><meta charset="utf-8">
    <title>FirstTry Dashboard</title>
    <style>body{{font:14px system-ui}}td,th{{border:1px solid #ddd;padding:6px}}table{{border-collapse:collapse}}</style>
    <h2>FirstTry ROI Dashboard</h2>
    <p><b>Total cache hits:</b> {total_hits} &nbsp; <b>Total local runs:</b> {total_runs} &nbsp; <b>Estimated time saved:</b> {total_saved/1000:.2f}s</p>
    <h3>Run History</h3>
    <table><thead><tr><th>Report</th><th>When</th><th>Cache Hits</th><th>Local Runs</th><th>Saved (ms)</th></tr></thead>
    <tbody>{''.join(rows)}</tbody></table>
    <h3>Top Failing Checks</h3>{_ol(top_fail)}
    <h3>Most Flaky Checks</h3>{_ol(flaky)}"""
    (repo_root / out).write_text(html_doc)
