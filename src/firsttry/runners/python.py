# src/firsttry/runners/python.py
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from .base import BaseRunner, RunnerResult

_MYPY_CODE_RE = re.compile(r"\[([a-zA-Z0-9_-]+)\]")


def _discover_test_paths(root: str) -> List[str]:
    root_path = Path(root)
    if (root_path / "tests").exists():
        return ["tests"]
    if (root_path / "test").exists():
        return ["test"]

    found: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        if ".venv" in dirpath or "venv" in dirpath or ".git" in dirpath:
            continue
        name = os.path.basename(dirpath)
        if name in ("tests", "test", "integration", "e2e"):
            found.append(dirpath)
            continue
        if any(f.startswith("test_") and f.endswith(".py") for f in filenames):
            found.append(dirpath)
    return found or ["."]
    

def _discover_python_roots(root: str) -> List[str]:
    candidates: List[str] = []
    for dirpath, _, _ in os.walk(root):
        if ".git" in dirpath or ".venv" in dirpath or "venv" in dirpath:
            continue
        p = Path(dirpath)
        if (p / "pyproject.toml").exists() or (p / ".ruff.toml").exists() or (p / "ruff.toml").exists():
            candidates.append(dirpath)
    return candidates or ["."]
    

def _find_ci_cmd(ci_plan: List[Dict[str, str]], tool: str) -> str | None:
    for item in ci_plan:
        if item["tool"] == tool:
            return item["cmd"]
    return None


class RuffRunner(BaseRunner):
    tool = "ruff"

    async def run(self, idx: int, ctx: Dict[str, Any], item: Dict[str, Any]) -> RunnerResult:
        name = f"lint[{idx}]"
        repo_root = ctx.get("repo_root", ".")
        ci_plan = ctx.get("ci_plan") or []
        # 1) CI wins
        ci_cmd = _find_ci_cmd(ci_plan, "ruff")
        if ci_cmd:
            cmd = item.get("cmd") or ci_cmd
        else:
            roots = _discover_python_roots(repo_root)
            paths = " ".join(roots)
            cmd = item.get("cmd") or f"ruff --format=json {paths}"

        res = await self.run_cmd(name, "ruff", cmd)
        # parse JSON if present
        try:
            data = json.loads(res.message)
            if isinstance(data, list):
                if not data:
                    res.message = "ruff: clean"
                else:
                    res.message = f"ruff: {len(data)} issues"
                    first = data[0]
                    res.code = first.get("code") or ""
        except Exception:
            pass
        return res


class MypyRunner(BaseRunner):
    tool = "mypy"

    async def run(self, idx: int, ctx: Dict[str, Any], item: Dict[str, Any]) -> RunnerResult:
        name = f"type[{idx}]"
        cmd = item.get("cmd") or "mypy ."
        res = await self.run_cmd(name, "mypy", cmd)
        if not res.ok:
            m = _MYPY_CODE_RE.search(res.message)
            if m:
                res.code = m.group(1)
        return res


class PytestRunner(BaseRunner):
    tool = "pytest"

    async def run(self, idx: int, ctx: Dict[str, Any], item: Dict[str, Any]) -> RunnerResult:
        name = f"tests[{idx}]"
        repo_root = ctx.get("repo_root", ".")
        ci_plan = ctx.get("ci_plan") or []
        # 1) CI wins
        ci_cmd = _find_ci_cmd(ci_plan, "pytest")
        if ci_cmd:
            cmd = item.get("cmd") or ci_cmd
        else:
            test_paths = _discover_test_paths(repo_root)
            cmd = item.get("cmd") or f"pytest -q {' '.join(test_paths)}"
        return await self.run_cmd(name, "pytest", cmd)


class BanditRunner(BaseRunner):
    tool = "bandit"

    async def run(self, idx: int, ctx: Dict[str, Any], item: Dict[str, Any]) -> RunnerResult:
        name = f"security[{idx}]"
        cmd = item.get("cmd") or "bandit -q -r ."
        return await self.run_cmd(name, "bandit", cmd)