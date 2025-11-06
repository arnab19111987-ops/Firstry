# src/firsttry/checks_orchestrator.py
from __future__ import annotations
import asyncio
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

from .check_registry import CHECK_REGISTRY
from . import cache as ft_cache

MAX_WORKERS = min(4, os.cpu_count() or 2)


async def run_subprocess(cmd: List[str], cwd: str | None = None) -> Tuple[int | None, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    return proc.returncode, stdout.decode("utf-8", "replace")


async def _bounded_run(cmd: List[str], sem: asyncio.Semaphore, cwd: str | None = None):
    async with sem:
        return await run_subprocess(cmd, cwd=cwd)


def _glob_inputs(repo_root: Path, patterns: List[str]) -> List[Path]:
    """
    Turn registry input patterns into concrete files.
    Current version is naive (repo_root.glob).
    TODO: for very large repos, consider:
      - `git ls-files` + fnmatch
      - or a prebuilt index
    """
    if not patterns:
        return []
    out: List[Path] = []
    for pat in patterns:
        out.extend(repo_root.glob(pat))
    return out


def _tool_input_hash(repo_root: Path, tool_name: str) -> str:
    meta = CHECK_REGISTRY.get(tool_name, {})
    patterns = meta.get("inputs", [])
    files = _glob_inputs(repo_root, patterns)
    return ft_cache.sha256_of_paths(files)


def _tool_to_cmd(tool_name: str) -> List[str]:
    # map logical tool → actual command
    if tool_name == "ruff":
        return ["ruff", "."]
    if tool_name == "repo_sanity":
        return ["python", "-m", "firsttry.repo_state", "check"]
    if tool_name == "black_check":
        # if later you support "black --diff", put it here
        return ["black", "--check", "."]
    if tool_name == "mypy":
        return ["mypy", "."]
    if tool_name == "pytest":
        return ["pytest", "-q"]
    if tool_name == "npm_test":
        return ["npm", "test", "--", "--watch=false"]
    if tool_name == "ci_parity":
        return ["python", "-m", "firsttry.ci_mapper", "check"]
    return ["echo", f"Unknown tool {tool_name}"]


async def run_checks_for_profile(
    repo_root: str,
    checks: List[str],
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Run checks in 3 buckets:
      1) fast (parallel)
      2) mutating (serial)
      3) slow (parallel, cache disabled if a mutator ran)
    """
    root = Path(repo_root)
    results: Dict[str, Any] = {}

    # ─────────────────────────────
    # 1) FAST
    # ─────────────────────────────
    fast_checks = [c for c in checks if CHECK_REGISTRY[c]["bucket"] == "fast"]
    print(f"⚡ FAST ({len(fast_checks)} checks)")
    fast_sem = asyncio.Semaphore(MAX_WORKERS)
    fast_tasks = []

    for chk in fast_checks:
        inp_hash = _tool_input_hash(root, chk)
        if use_cache and ft_cache.is_tool_cache_valid(repo_root, chk, inp_hash):
            print(f"  ✅ {chk} (cached)")
            results[chk] = {"status": "ok", "cached": True, "elapsed": 0.0}
            continue
        cmd = _tool_to_cmd(chk)
        fast_tasks.append((chk, inp_hash, _bounded_run(cmd, fast_sem, cwd=repo_root)))

    for chk, inp_hash, coro in fast_tasks:
        start = time.monotonic()
        rc, out = await coro
        elapsed = time.monotonic() - start
        if rc == 0:
            ft_cache.write_tool_cache(
                repo_root, chk, inp_hash, "ok", {"elapsed": elapsed}
            )
            print(f"  ✅ {chk} ({elapsed:.2f}s)")
        else:
            ft_cache.write_tool_cache(
                repo_root, chk, inp_hash, "fail", {"elapsed": elapsed, "output": out}
            )
            print(f"  ❌ {chk} ({elapsed:.2f}s)")
        results[chk] = {
            "status": "ok" if rc == 0 else "fail",
            "output": out,
            "elapsed": elapsed,
        }

    # ─────────────────────────────
    # 2) MUTATING (serial)
    # ─────────────────────────────
    mutating_ran = False
    mut_checks = [c for c in checks if CHECK_REGISTRY[c]["bucket"] == "mutating"]
    if mut_checks:
        print(f"\n🛠 MUTATING ({len(mut_checks)} checks)")
    for chk in mut_checks:
        inp_hash = _tool_input_hash(root, chk)
        # for mutating checks we are conservative: do NOT read cache
        cmd = _tool_to_cmd(chk)
        start = time.monotonic()
        rc, out = await run_subprocess(cmd, cwd=repo_root)
        elapsed = time.monotonic() - start
        if rc == 0:
            mutating_ran = True
            ft_cache.write_tool_cache(
                repo_root, chk, inp_hash, "ok", {"elapsed": elapsed}
            )
            print(f"  ✅ {chk} ({elapsed:.2f}s)")
        else:
            ft_cache.write_tool_cache(
                repo_root, chk, inp_hash, "fail", {"elapsed": elapsed, "output": out}
            )
            print(f"  ❌ {chk} ({elapsed:.2f}s)")
        results[chk] = {
            "status": "ok" if rc == 0 else "fail",
            "output": out,
            "elapsed": elapsed,
        }

    # ─────────────────────────────
    # 3) SLOW (parallel)
    # ─────────────────────────────
    slow_checks = [c for c in checks if CHECK_REGISTRY[c]["bucket"] == "slow"]
    if slow_checks:
        print(f"\n🐌 SLOW ({len(slow_checks)} checks, running in parallel)")

    # IMPORTANT: if any mutating check ran, do NOT trust cache for slow ones
    use_cache_for_slow = use_cache and not mutating_ran

    slow_sem = asyncio.Semaphore(MAX_WORKERS)
    slow_tasks = []
    for chk in slow_checks:
        inp_hash = _tool_input_hash(root, chk)
        if use_cache_for_slow and ft_cache.is_tool_cache_valid(
            repo_root, chk, inp_hash
        ):
            print(f"  ✅ {chk} (cached)")
            results[chk] = {"status": "ok", "cached": True, "elapsed": 0.0}
            continue
        cmd = _tool_to_cmd(chk)
        slow_tasks.append((chk, inp_hash, _bounded_run(cmd, slow_sem, cwd=repo_root)))

    for chk, inp_hash, coro in slow_tasks:
        start = time.monotonic()
        rc, out = await coro
        elapsed = time.monotonic() - start
        if rc == 0:
            ft_cache.write_tool_cache(
                repo_root, chk, inp_hash, "ok", {"elapsed": elapsed}
            )
            print(f"  ✅ {chk} ({elapsed:.2f}s)")
        else:
            ft_cache.write_tool_cache(
                repo_root, chk, inp_hash, "fail", {"elapsed": elapsed, "output": out}
            )
            print(f"  ❌ {chk} ({elapsed:.2f}s)")
        results[chk] = {
            "status": "ok" if rc == 0 else "fail",
            "output": out,
            "elapsed": elapsed,
        }

    # ─────────────────────────────
    # Summary timing
    # ─────────────────────────────
    total_elapsed = sum(r.get("elapsed", 0.0) for r in results.values())
    print(
        f"\n⏱  Total active check time (not counting cache hits): {total_elapsed:.2f}s"
    )

    return results
