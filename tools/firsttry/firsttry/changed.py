from __future__ import annotations
from subprocess import run, PIPE
from typing import Iterable, List


def get_changed_files(base_ref: str = "HEAD") -> List[str]:
    """
    Returns a list of changed file paths since base_ref (ACMRT changes).
    Falls back to [] if git is unavailable.
    """
    try:
        proc = run(
            ["git", "diff", "--name-only", "--diff-filter=ACMRT", base_ref],
            check=False,
            stdout=PIPE,
            stderr=PIPE,
            text=True,
        )
        if proc.returncode != 0:
            return []
        files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        return files
    except Exception:
        return []


def filter_python(files: Iterable[str]) -> List[str]:
    return [f for f in files if f.endswith(".py")]
