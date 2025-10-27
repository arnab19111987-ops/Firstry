from __future__ import annotations

import os
import stat
from typing import Tuple
from pathlib import Path


PRE_COMMIT_HOOK = """#!/bin/sh
export FIRSTTRY_USE_STUB_RUNNERS=0
python -m firsttry.cli run --gate pre-commit
status=$?
if [ $status -ne 0 ]; then
    echo ""
    echo "FirstTry blocked this commit ❌"
    echo "Fix the issues above, then commit again."
    exit $status
fi
exit 0
"""

PRE_PUSH_HOOK = """#!/bin/sh
export FIRSTTRY_USE_STUB_RUNNERS=0
python -m firsttry.cli run --gate pre-push
status=$?
if [ $status -ne 0 ]; then
    echo ""
    echo "FirstTry blocked this push ❌"
    echo "Fix the issues above, then push again."
    exit $status
fi
exit 0
"""


def _write_executable(path: str | Path, content: str) -> None:
    path = str(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_git_hooks(repo_root: str | Path = ".") -> Tuple[Path, Path]:
    repo_root = Path(repo_root)
    hooks_dir = repo_root / ".git" / "hooks"
    pre_commit_path = hooks_dir / "pre-commit"
    pre_push_path = hooks_dir / "pre-push"

    _write_executable(pre_commit_path, PRE_COMMIT_HOOK)
    _write_executable(pre_push_path, PRE_PUSH_HOOK)

    return pre_commit_path, pre_push_path


def install_pre_commit_hook(repo_root: str | Path | None = None) -> Path:
    """Compatibility wrapper used by tests: write the pre-commit hook and
    return the path to the created hook.
    """
    repo_root = repo_root or "."
    pre_commit, _ = install_git_hooks(repo_root)
    return pre_commit


def install_pre_push_hook(repo_root: str | Path | None = None) -> Path:
    """Write the pre-push hook and return the path."""
    repo_root = repo_root or "."
    _, pre_push = install_git_hooks(repo_root)
    return pre_push
