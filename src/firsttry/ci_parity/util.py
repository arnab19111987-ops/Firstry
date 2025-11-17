from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def current_repo_root() -> Path:
    """Resolve the repository root dynamically from FT_REPO_ROOT or cwd.

    This allows tests to set FT_REPO_ROOT via environment before invoking
    functions that rely on the repo location.
    """
    return Path(os.environ.get("FT_REPO_ROOT", Path.cwd())).resolve()


@dataclass
class Step:
    id: str
    cmd: List[str]
    env: Dict[str, str] | None = None
    cwd: Optional[Path] = None
    allow_fail: bool = False


class ExecError(RuntimeError):
    pass


def run_step(step: Step, dryrun: bool = False) -> Tuple[int, str]:
    env = os.environ.copy()
    if step.env:
        env.update(step.env)
    cwd = str(step.cwd or current_repo_root())
    # Final safety: drop stray '\\' tokens that can appear from malformed splits
    safe_cmd = [t for t in step.cmd if t != "\\"]
    if dryrun or os.environ.get("FT_CI_PARITY_DRYRUN") == "1":
        return 0, f"[dryrun] ({step.id}) {' '.join(safe_cmd)}"
    proc = subprocess.run(safe_cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if proc.returncode != 0 and not step.allow_fail:
        raise ExecError(
            f"[{step.id}] failed ({proc.returncode})\n"
            f"CMD: {' '.join(safe_cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc.returncode, proc.stdout + proc.stderr


def has_dir(name: str) -> bool:
    return (current_repo_root() / name).is_dir()


def staged_or_changed_paths() -> List[str]:
    # Prefer staged files; fallback to changed files.
    try:
        out = (
            subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=str(current_repo_root()),
                capture_output=True,
                text=True,
                check=True,
            )
            .stdout.strip()
            .splitlines()
        )
        if not out:
            out = (
                subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    cwd=str(current_repo_root()),
                    capture_output=True,
                    text=True,
                    check=True,
                )
                .stdout.strip()
                .splitlines()
            )
        return [p for p in out if p.endswith(".py")]
    except Exception:
        return []


def existing(*candidates: str) -> List[str]:
    return [c for c in candidates if (current_repo_root() / c).exists()]


def guess_test_paths() -> List[str]:
    paths = []
    for cand in ("tests", "test", "tools/firsttry/tests"):
        if (current_repo_root() / cand).exists():
            paths.append(cand)
    return paths


def grep_any(lines: List[str], *needles: str) -> bool:
    s = "\n".join(lines)
    return any(n in s for n in needles)


def tokenize_shell_line(line: str) -> List[str]:
    """
    Tokenize a shell command line robustly.
    - Uses shlex.split (POSIX) to honor quotes/escapes.
    - Handles cases like: pytest -q -m "not slow"
    - Avoids leaking stray backslashes as tokens.
    """
    try:
        return shlex.split(line, posix=True)
    except ValueError:
        # Fall back to whitespace split if the line is badly quoted
        return [t for t in line.strip().split() if t]


def normalize_cmd(cmd: List[str]) -> List[str]:
    # Strip trivial surrounding quotes, keep list
    out = []
    for c in cmd:
        # Drop standalone backslash tokens (defensive)
        if c == "\\":
            continue
        out.append(c.strip('"').strip("'"))
    return out
