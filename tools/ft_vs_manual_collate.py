#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path(".firsttry/bench")
LOGS = ROOT / "logs"
RPTS = ROOT / "reports"
OUT_JSON = ROOT / "compare_summary.json"
OUT_MD = ROOT / "compare_summary.md"


def load_json(p: Path):
    if not p.exists():
        return None
    return json.loads(p.read_text() or "{}")


def parse_manual_result(name: str):
    data = load_json(LOGS / f"{name}.json")
    if not data:
        return None
    rc = int(data.get("rc", 0))
    elapsed = float(data.get("elapsed_s", 0.0))
    out = (data.get("stdout") or "") + (data.get("stderr") or "")
    # Error counts per tool (heuristics)
    if name == "manual_ruff":
        # stdout is empty because we captured JSON; recount from stderr if needed.
        # But our timing wrapper returns stdout; we called ruff with --output-format json, so count "code" entries.
        try:
            r = json.loads(data.get("stdout") or "[]")
            errs = len(r)
        except Exception:
            errs = len(re.findall(r"^[A-Z].+:\d+:\d+:", out, flags=re.MULTILINE))
    elif name == "manual_mypy":
        # Count "error:" lines
        errs = len(re.findall(r": error:", out))
    elif name == "manual_pytest":
        # Parse summary line: "X passed, Y failed, Z skipped ..."
        m = re.search(r"(\d+)\s+failed", out)
        fails = int(m.group(1)) if m else 0
        errs = fails
    elif name == "manual_bandit":
        try:
            j = json.loads(data.get("stdout") or "{}")
            errs = len(j.get("results", []))
        except Exception:
            errs = len(re.findall(r"Issue:\s", out))
    else:
        errs = 0
    return {"rc": rc, "elapsed_s": elapsed, "errors": errs}


def load_ft_reports(tier: str):
    cold = load_json(RPTS / f"ft_{tier}_cold.json") or {}
    warm = load_json(RPTS / f"ft_{tier}_warm.json") or {}
    return cold.get("checks", {}), warm.get("checks", {})


def ft_check(checks: dict, key_prefix: str):
    # find first check whose id starts with prefix (e.g., 'ruff', 'mypy', 'pytest', 'bandit')
    for k, v in checks.items():
        if (
            k.startswith(key_prefix + ":")
            or k == key_prefix
            or v.get("meta", {}).get("check_id") == key_prefix
        ):
            return {
                "status": v.get("status"),
                "cache_status": v.get("cache_status"),
                "duration_ms": v.get("duration_ms"),
                "stdout": v.get("stdout", ""),
                "stderr": v.get("stderr", ""),
            }
    return None


def errors_from_text(tool: str, text: str):
    if not text:
        return 0
    if tool == "ruff":
        return len(re.findall(r"^[A-Z].+:\d+:\d+:", text, flags=re.MULTILINE))
    if tool == "mypy":
        return len(re.findall(r": error:", text))
    if tool == "pytest":
        m = re.search(r"(\d+)\s+failed", text)
        return int(m.group(1)) if m else 0
    if tool == "bandit":
        return len(re.findall(r"Issue:\s", text))
    return 0


def main():
    tier = "lite"  # align with sweep default
    # Manual
    m_ruff = parse_manual_result("manual_ruff")
    m_mypy = parse_manual_result("manual_mypy")
    m_pytest = parse_manual_result("manual_pytest")
    m_bandit = parse_manual_result("manual_bandit")

    # FT
    cold, warm = load_ft_reports(tier)
    f_ruff_c = ft_check(cold, "ruff")
    f_ruff_w = ft_check(warm, "ruff")
    f_mypy_c = ft_check(cold, "mypy")
    f_mypy_w = ft_check(warm, "mypy")
    f_py_c = ft_check(cold, "pytest")
    f_py_w = ft_check(warm, "pytest")
    f_ban_c = ft_check(cold, "bandit")
    f_ban_w = ft_check(warm, "bandit")

    rows = []

    def add(tool, m, fc, fw):
        if not m and not fc:
            return
        ft_ms = (fw or fc or {}).get("duration_ms")
        ft_errs = None
        # Derive FT error counts from FT outputs if present (stdout/stderr)
        src_txt = ((fw or {}).get("stdout") or "") + ((fw or {}).get("stderr") or "")
        if not src_txt:
            src_txt = ((fc or {}).get("stdout") or "") + ((fc or {}).get("stderr") or "")
        if src_txt:
            ft_errs = errors_from_text(tool, src_txt)

        speedup = None
        if m and ft_ms not in (None, 0):
            speedup = round((m["elapsed_s"] * 1000) / ft_ms, 2)

        parity = None
        if m is not None and ft_errs is not None:
            parity = "OK" if (m["errors"] == ft_errs) else f"DIFF(man={m['errors']}, ft={ft_errs})"

        rows.append(
            {
                "tool": tool,
                "manual_s": (m or {}).get("elapsed_s"),
                "manual_rc": (m or {}).get("rc"),
                "manual_errors": (m or {}).get("errors"),
                "ft_ms": ft_ms,
                "ft_status_warm": (fw or {}).get("status") or (fc or {}).get("status"),
                "ft_cache_warm": (fw or {}).get("cache_status"),
                "ft_errors": ft_errs,
                "speedup_x": speedup,
                "parity": parity,
            },
        )

    add("ruff", m_ruff, f_ruff_c, f_ruff_w)
    add("mypy", m_mypy, f_mypy_c, f_mypy_w)
    add("pytest", m_pytest, f_py_c, f_py_w)
    add("bandit", m_bandit, f_ban_c, f_ban_w)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"tier": tier, "rows": rows}, indent=2))

    # Markdown
    lines = []
    lines.append(f"# FT vs Manual — Tier `{tier}`\n")
    lines.append(
        "| Tool | Manual (s) | Manual errors | FT (ms, warm) | FT status | Cache | FT errors | Speedup× | Parity |",
    )
    lines.append("|---|---:|---:|---:|:--:|:--:|---:|---:|:--:|")
    for r in rows:
        lines.append(
            f"| {r['tool']} | {r.get('manual_s') if r.get('manual_s') is not None else ''} "
            f"| {r.get('manual_errors') if r.get('manual_errors') is not None else ''} "
            f"| {r.get('ft_ms') if r.get('ft_ms') is not None else ''} "
            f"| {r.get('ft_status_warm') or ''} | {r.get('ft_cache_warm') or ''} "
            f"| {r.get('ft_errors') if r.get('ft_errors') is not None else ''} "
            f"| {r.get('speedup_x') if r.get('speedup_x') is not None else ''} "
            f"| {r.get('parity') or ''} |",
        )
    OUT_MD.write_text("\n".join(lines))
    print(f"Wrote {OUT_JSON} and {OUT_MD}")


if __name__ == "__main__":
    main()
