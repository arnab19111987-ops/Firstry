from __future__ import annotations

from typing import Iterable, List
import sys
import subprocess as _subprocess


# IMPORTANT:
# We keep a module-level alias called `run` so tests can monkeypatch
# `firsttry.changed.run = fake_run` and expect get_changed_files() to
# use it.
#
# However, when pytest runs the full suite, sometimes two different
# copies of the module get imported (editable install layout, tools/
# overlay etc). In that case, the test may patch the *other* module
# object, not the exact instance that get_changed_files() closes over.
#
# To handle that, _get_runner() below will look up the canonical
# sys.modules["firsttry.changed"] object at call time and prefer its
# `run` attribute if present. That makes the monkeypatch deterministic
# even under weird import duplication.
run = _subprocess.run  # default fallback


def _get_runner():
    """
    Resolve the best 'run' function to execute git.

    Priority:
    1. If sys.modules["firsttry.changed"].run exists (this is what tests
       monkeypatch), return that.
    2. Fallback to this module's own `run`.
    3. Fallback to subprocess.run.
    """
    # Step 1: try the canonical module in sys.modules
    mod = sys.modules.get("firsttry.changed")
    if mod is not None:
        maybe = getattr(mod, "run", None)
        if callable(maybe):
            return maybe  # monkeypatched target wins

    # Step 2: try our local alias
    if callable(run):
        return run

    # Step 3: absolute fallback
    return _subprocess.run


def _git_diff_name_only(rev: str) -> List[str]:
    """
    Internal helper to collect changed file paths from git.

    Returns [] instead of raising if git fails or repo doesn't exist.
    """
    runner = _get_runner()

    try:
        proc = runner(
            ["git", "diff", "--name-only", rev],
            check=False,
            stdout=_subprocess.PIPE,
            stderr=_subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        # 'git' not available in environment
        return []
    except Exception:
        # Be very forgiving in test/CI environments
        return []

    # If whatever we called didn't behave like subprocess.run and doesn't
    # have .returncode/.stdout, degrade gracefully.
    returncode = getattr(proc, "returncode", 0)
    if returncode != 0:
        return []

    stdout = getattr(proc, "stdout", "") or ""
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    return lines


def filter_python(paths: Iterable[str]) -> List[str]:
    """
    Keep only .py files for selective checks (used by quick gates).
    """
    out: List[str] = []
    for p in paths:
        if p.endswith(".py"):
            out.append(p)
    return out


def get_changed_files(rev: str = "HEAD") -> List[str]:
    """
    Public API:
    - get list of changed files compared to `rev`
    - normalize slashes
    - dedupe
    - return sorted list
    """
    raw = _git_diff_name_only(rev)

    normed: List[str] = []
    for p in raw:
        cleaned = p.replace("//", "/").strip()
        if cleaned:
            normed.append(cleaned)

    # dedupe deterministically
    return sorted(dict.fromkeys(normed))
