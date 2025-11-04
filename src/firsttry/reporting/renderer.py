from __future__ import annotations
from pathlib import Path
import json
from typing import Dict
from ..executor.dag import TaskResult


def render_tty(results: Dict[str, TaskResult], *, show_fail_output: bool = True, max_lines: int = 80) -> None:
    fails: list[TaskResult] = []
    hits = runs = 0

    for tid, r in results.items():
        is_cache = r.status.startswith("hit-")
        prefix = "[CACHE]" if is_cache else "[ RUN ]"
        print(f"{prefix} {r.status.upper():10s} {tid} ({r.duration_ms}ms)")
        if is_cache:
            hits += 1
        else:
            runs += 1
        if r.status in {"fail", "error"}:
            fails.append(r)

    print(f"\n{hits} checks verified from cache, {runs} run locally.\n")

    if show_fail_output and fails:
        print("— FAIL DETAILS —")
        for r in fails:
            print(f"\n[{r.id}] status={r.status}")

            def _clip(s: str) -> str:
                if not s:
                    return ""
                lines = s.splitlines()
                if len(lines) > max_lines:
                    head = "\n".join(lines[:max_lines])
                    return f"{head}\n... (truncated {len(lines)-max_lines} lines)"
                return s

            if r.stdout:
                print("\nSTDOUT:")
                print(_clip(r.stdout))
            if r.stderr:
                print("\nSTDERR:")
                print(_clip(r.stderr))


def write_json(repo_root: Path, results: Dict[str, TaskResult], out: str = ".firsttry/report.json") -> None:
    payload = {"checks": {tid: r.to_report_json() for tid, r in results.items()}}
    p = repo_root / out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

# Hooks to add later:
# def write_junit_xml(...): ...
# def write_html_report(...): ...
