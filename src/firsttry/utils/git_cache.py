from __future__ import annotations

from pathlib import Path
from typing import Sequence
from ..proc import run_cmd

_GIT_CACHE: dict = {}


def git_ls(repo: Path, *patterns: str) -> list[str]:
    """Return git-tracked files matching patterns. Cache results per-process.

    Patterns are passed to `git ls-files -- <patterns>`; if no patterns given,
    returns all tracked files.
    """
    repo = Path(repo)
    key = (str(repo), tuple(patterns))
    if key in _GIT_CACHE:
        return _GIT_CACHE[key]

    args = ["git", "ls-files"]
    if patterns:
        args += ["--"] + list(patterns)

    try:
        proc = run_cmd(args, cwd=str(repo), capture_output=True, text=True)
    except Exception:
        _GIT_CACHE[key] = []
        return []

    if proc.returncode != 0:
        _GIT_CACHE[key] = []
        return []

    out = proc.stdout or ""
    files = [ln for ln in out.splitlines() if ln]
    _GIT_CACHE[key] = files
    return files
