from __future__ import annotations

import os
import stat
from typing import Tuple
from pathlib import Path
from .license import ensure_trial_license_if_missing, license_summary_for_humans


PRE_COMMIT_SCRIPT = """#!/bin/sh
# FirstTry pre-commit hook
# tries venv first, then global
if command -v firsttry >/dev/null 2>&1; then
  firsttry run --level 2
else
  python -m firsttry run --level 2
fi
status=$?
if [ $status -ne 0 ]; then
  echo "FirstTry: pre-commit failed."
  exit $status
fi
"""

PRE_PUSH_SCRIPT = """#!/bin/sh
# FirstTry pre-push hook
# tries venv first, then global
if command -v firsttry >/dev/null 2>&1; then
  firsttry run --level 3
else
  python -m firsttry run --level 3
fi
status=$?
if [ $status -ne 0 ]; then
  echo "FirstTry: pre-push failed."
  exit $status
fi
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

    _write_executable(pre_commit_path, PRE_COMMIT_SCRIPT)
    _write_executable(pre_push_path, PRE_PUSH_SCRIPT)

    return pre_commit_path, pre_push_path


def install_hooks_and_bootstrap_trial(repo_root: str | Path = ".") -> None:
    """
    Convenience wrapper: install git hooks and ensure a short trial license is present.
    Prints onboarding information including the human-friendly license summary.
    """
    # 1. install hooks using existing logic
    install_git_hooks(repo_root)

    # 2. ensure a small trial license exists (best-effort)
    lic_obj = ensure_trial_license_if_missing(days=3)

    # 3. onboarding messages
    print("")
    print("✅ Git hooks installed (pre-commit / pre-push).")
    print("✅ Trial license bootstrapped.")
    try:
        print(license_summary_for_humans(lic_obj))
    except Exception:
        # avoid crashing installers if summary formatting fails
        pass
    print("")
    print("You're now in trial mode. Run:")
    print("  python3 -m firsttry.cli run --gate pre-commit")


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


def hooks_installed(repo_root: str | Path = ".") -> bool:
    """Check if FirstTry git hooks are installed."""
    repo_root = Path(repo_root)
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return False

    pre_commit_hook = git_dir / "hooks" / "pre-commit"
    pre_push_hook = git_dir / "hooks" / "pre-push"

    return pre_commit_hook.exists() and pre_push_hook.exists()


def install_all_hooks(repo_root: str | Path = ".") -> bool:
    """Install all FirstTry git hooks and return True if successful."""
    repo_root = Path(repo_root)
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return False

    try:
        install_git_hooks(repo_root)
        return True
    except Exception:
        return False
