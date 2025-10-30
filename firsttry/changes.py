from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


def get_changed_files(root: Path, since_ref: str | None) -> List[str]:
    """
    Return list of files changed since `since_ref` using git.
    If `since_ref` is None or git is unavailable → return [].
    """
    if since_ref is None:
        return []
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", since_ref, "--"],
            cwd=str(root),
            text=True,
        )
    except Exception:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]
