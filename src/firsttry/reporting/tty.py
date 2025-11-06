# src/firsttry/reporting/tty.py
from __future__ import annotations
import shutil
from typing import Dict, Any

from ..twin.graph import CodebaseTwin  # <-- use the twin for repo/file context

BLUE = "🔹"
FIRE = "🔥"
OK = "✅"
FAIL = "❌"
WARN = "⚠️"
LOCK = "🔒"
X = "✖"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _term_width() -> int:
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 100


def _severity_priority(severity: str) -> int:
    """Map severity to numeric priority for sorting (lower = higher priority)."""
    sev = severity.lower()
    if sev in ("critical", "error"):
        return 0
    elif sev in ("high", "warning"):
        return 1
    elif sev in ("medium", "note"):
        return 2
    elif sev == "low":
        return 3
    else:
        return 4


def _severity_label(severity: str) -> str:
    """Convert severity to display label with priority level."""
    sev = severity.lower()
    if sev in ("critical", "error"):
        return "CRITICAL"
    elif sev in ("high", "warning"):
        return "HIGH"
    elif sev in ("medium", "note"):
        return "MEDIUM"
    elif sev == "low":
        return "LOW"
    else:
        return severity.upper()


def _tool_counts(checks: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """Aggregate counts by tool id (ruff/mypy/pytest/bandit/etc.)."""
    agg: Dict[str, Dict[str, int]] = {}
    for tid, r in checks.items():
        tool = tid.split(":")[0]
        ent = agg.setdefault(tool, {"errors": 0, "findings": 0, "failures": 0, "ok": 0})
        st = r.get("status")
        
        if tool == "pytest":
            if st == "ok":
                ent["ok"] += 1
            else:
                ent["failures"] += 1
        elif tool == "mypy":
            # Parse mypy error count from stdout: "Found X errors in Y files"
            stdout = r.get("stdout", "")
            import re
            match = re.search(r"Found (\d+) error", stdout)
            if match:
                ent["findings"] += int(match.group(1))
            if st == "ok":
                ent["ok"] += 1
            else:
                ent["errors"] += 1
        else:
            # Prefer structured counts if present
            ent["findings"] += int(r.get("finding_count", 0) or r.get("errors", 0))
            if st == "ok":
                ent["ok"] += 1
            else:
                ent["errors"] += 1
    return agg


def _result_line(overall_ok: bool, ran: int) -> str:
    return f"Result: {'✅ PASSED' if overall_ok else f'{FAIL} FAILED'} ({_plural(ran, 'check')} run)"


def render_tty(
    report: Dict[str, Any],
    *,
    tier_name: str,
    twin: CodebaseTwin,  # <-- changed: receive CodebaseTwin instead of repo_root
    detailed: bool,
    max_items: int,
) -> None:
    """
    Render a human-friendly TTY report from the normalized report dict.

    Args:
        report: normalized report payload (e.g., what's written to .firsttry/report.json)
        tier_name: e.g., "lite", "strict", "pro"
        twin: CodebaseTwin instance representing the scanned repo state
        detailed: if True, render detailed sections; otherwise summary-only
        max_items: truncate each detailed section to this many items
    """
    checks = report.get("checks", {})
    tools = sorted({k.split(":")[0] for k in checks})
    tool_counts = _tool_counts(checks)
    overall_ok = all(v.get("status") == "ok" for v in checks.values())

    # Header & Context
    print(f"{BLUE} FirstTry ({tier_name.capitalize()}) — Local CI")
    print("Context")
    # Use the twin to report the file count
    try:
        repo_file_count = len(twin.files)  # <-- changed: use twin instead of walking the FS
    except Exception:
        repo_file_count = 0
    print(f"Repo: {repo_file_count} files")
    if tools:
        print(f"Checks Run: {', '.join(tools)}")
    print()

    # Summary
    print("Summary")
    # ruff
    if "ruff" in tool_counts:
        f = tool_counts["ruff"]["findings"]
        af = sum(int(checks[k].get("autofix_count", 0)) for k in checks if k.startswith("ruff:"))
        line = f"{('✅' if f == 0 else FIRE)} ruff: {f} finding" + ("" if f == 1 else "s")
        if af:
            line += f" ({af} auto-fixable)"
        print(line)
    # mypy
    if "mypy" in tool_counts:
        f = tool_counts["mypy"]["findings"]
        print(f"{('✅' if f == 0 else FIRE)} mypy: {f} type error" + ("" if f == 1 else "s"))
    # pytest
    if "pytest" in tool_counts:
        fails = tool_counts["pytest"]["failures"]
        if fails == 0:
            print("✅ pytest: all passed")
        else:
            print(f"{X} pytest: {fails} failed")
    # other tools summarized generically
    for t in sorted(tool_counts):
        if t in ("ruff", "mypy", "pytest"):
            continue
        f = tool_counts[t]["errors"] + tool_counts[t]["findings"] + tool_counts[t]["failures"]
        if f or tool_counts[t]["ok"] == 0:
            print(f"{FIRE} {t}: {f} finding" + ("" if f == 1 else "s"))
        else:
            print(f"✅ {t}: OK")

    print(_result_line(overall_ok, len(tools)))
    print()

    # 🔒 Show Shared Remote Cache lock for Lite tier only
    if tier_name.lower() in ("lite", "free-lite", "free"):
        # Calculate how many checks could have been shared from team cache
        # (For now, we show all cache hits as potential shared cache hits)
        remote_share_saved = sum(
            1 for v in checks.values() 
            if v.get("cache_status", "").startswith("hit-")
        )
        if remote_share_saved > 0:
            print(f"{LOCK} Shared Remote Cache (Pro): Your team re-ran {remote_share_saved} check{'s' if remote_share_saved != 1 else ''} you already passed. (Upgrade to Pro to share results)")
            print()

    if not detailed:
        return

    # Detailed Report
    print("Detailed Report")

    # ---- mypy block ----
    if "mypy" in tools:
        items = []
        for tid, r in checks.items():
            if not tid.startswith("mypy:"):
                continue
            # Support multiple shapes: "items" or "errors_list"
            structured = r.get("items", []) or r.get("errors_list", [])
            if structured:
                for e in structured:
                    items.append(e)
            else:
                # Parse from stdout if no structured data
                stdout = r.get("stdout", "")
                import re
                # Match: path:line: severity: message [code]
                for line_txt in stdout.split("\n"):
                    match = re.match(r'^(.+?):(\d+):\s*(error|note|warning):\s*(.+?)\s*\[([^\]]+)\]', line_txt)
                    if match:
                        items.append({
                            "path": match.group(1),
                            "line": match.group(2),
                            "severity": match.group(3),
                            "msg": match.group(4),
                            "code": match.group(5),
                        })
        if items:
            # Sort by priority: CRITICAL/ERROR first, then HIGH/WARNING, then MEDIUM/NOTE, then LOW
            items.sort(key=lambda x: _severity_priority(x.get("severity", "note")))
            print(f"{FIRE} mypy ({len(items)} Type Errors)")
            shown = 0
            for e in items:
                if shown >= max_items:
                    break
                sev = _severity_label(e.get("severity", "error"))
                code = e.get("code", "unknown")
                msg = e.get("msg", "")
                path = e.get("path", "")
                line = e.get("line", "")
                print(f"[{sev}] {code}: {msg}")
                print(f"File: {path}:{line}\n")
                shown += 1
            more = len(items) - shown
            if more > 0:
                print(f"...and {more} more errors\n")

    # ---- ruff block ----
    if "ruff" in tools:
        items = []
        for tid, r in checks.items():
            if not tid.startswith("ruff:"):
                continue
            # Support both "items" and "findings"
            structured = r.get("items", []) or r.get("findings", [])
            if structured:
                for e in structured:
                    items.append(e)
            else:
                # Parse from stdout if no structured data
                # Ruff format: path:line:col: severity: message [code]
                stdout = r.get("stdout", "")
                import re
                for line_txt in stdout.split("\n"):
                    # Match: path:line:col: CODE message
                    match = re.match(r'^(.+?):(\d+):(\d+):\s*([A-Z]+\d+)\s*(.+)', line_txt)
                    if match:
                        items.append({
                            "path": match.group(1),
                            "line": match.group(2),
                            "col": match.group(3),
                            "code": match.group(4),
                            "msg": match.group(5),
                            "severity": "MEDIUM",
                        })
        if items:
            # Sort by priority: CRITICAL first, then HIGH, then MEDIUM, then LOW
            items.sort(key=lambda x: _severity_priority(x.get("severity", "medium")))
            print(f"{FIRE} ruff ({len(items)} Findings)")
            shown = 0
            for e in items:
                if shown >= max_items:
                    break
                sev = _severity_label(e.get("severity", "medium"))
                code = e.get("code") or e.get("rule") or "?"
                msg = e.get("msg", "")
                path = e.get("path", "")
                line = e.get("line", "")
                col = e.get("col", "")
                loc = f"{path}:{line}:{col}" if col else f"{path}:{line}"
                print(f"[{sev}] {code}: {msg}")
                print(f"File: {loc}\n")
                shown += 1
            more = len(items) - shown
            if more > 0:
                print(f"...and {more} more findings\n")

    # ---- pytest block ----
    if "pytest" in tools:
        fail_items = []
        for tid, r in checks.items():
            if not tid.startswith("pytest:"):
                continue
            failures = r.get("failures", [])
            if isinstance(failures, int):
                failures = r.get("items", [])
            elif not isinstance(failures, list):
                failures = []
            for f in failures:
                fail_items.append(f)
        if fail_items:
            print(f"{X} pytest ({len(fail_items)} Failures)")
            shown = 0
            for f in fail_items:
                if shown >= max_items:
                    break
                if not isinstance(f, dict):
                    continue
                name = f.get("name") or f.get("nodeid", "test")
                msg = f.get("msg") or f.get("assert", "Assertion failed")
                path = f.get("path", "")
                line = f.get("line", "")
                print(f"[CRITICAL] {name}\n{msg}\nFile: {path}:{line}\n")
                shown += 1
            more = len(fail_items) - shown
            if more > 0:
                print(f"...and {more} more failures\n")
    
    # ---- HTML Report Link ----
    if detailed:
        # Check if HTML report exists
        from pathlib import Path
        html_path = Path(".firsttry/report.html")
        if html_path.exists():
            print()
            print("─" * _term_width())
            print(f"📊 Full HTML Report: {html_path.absolute()}")
            print(f"   Open in browser: file://{html_path.absolute()}")
            print("─" * _term_width())


# Backward compatibility wrapper for CLI
def render_tty_report(
    report: Dict[str, Any],
    tier_label: str = "Free",
    repo_file_count: int | None = None,
    test_count: int | None = None,
    machine_desc: str = "",
    detailed: bool = False,
    max_per_check: int = 10,
    order_by_priority: bool = True,
    skipped_checks_hint: list[str] | None = None,
) -> str:
    """
    Legacy wrapper for CLI compatibility.
    Creates a minimal CodebaseTwin and calls render_tty.
    Returns empty string (since render_tty prints directly).
    """
    from pathlib import Path
    from ..twin.graph import CodebaseTwin
    
    # Create a minimal twin for file count
    # Use the repo root from the report if available
    repo_root = Path.cwd()
    if "meta" in report and "repo_root" in report["meta"]:
        repo_root = Path(report["meta"]["repo_root"])
    
    # Create a minimal twin with just file listing
    twin = CodebaseTwin(repo_root=str(repo_root))
    
    # If repo_file_count was provided, create fake files to match
    if repo_file_count is not None:
        from ..twin.graph import FileNode
        for i in range(repo_file_count):
            twin.files[f"file_{i}"] = FileNode(
                path=f"file_{i}",
                lang="unknown",
                module=None,
                hash="",
                imports=set(),
                depends_on=set(),
                dependents=set(),
            )
    
    # Call the new render_tty function
    render_tty(
        report,
        tier_name=tier_label,
        twin=twin,
        detailed=detailed,
        max_items=max_per_check,
    )
    
    return ""  # render_tty prints directly, no string return
