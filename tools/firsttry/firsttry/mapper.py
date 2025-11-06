from __future__ import annotations

from collections.abc import Iterable
from pathlib import PurePath


def guess_test_kexpr(changed: Iterable[str]) -> str | None:
    """Heuristic: build a pytest -k expression from changed source filenames.
    - Map 'foo/bar/baz.py' → targets test names containing 'baz'
    - De-duplicate and ignore dunders/test files.
    """
    tokens: set[str] = set()
    for f in changed:
        p = PurePath(f)
        if p.name.startswith("test_"):
            stem = p.stem.replace("test_", "")
        else:
            stem = p.stem
        if stem and stem not in {"__init__", "__main__"}:
            tokens.add(stem)
    if not tokens:
        return None
    # e.g., (baz or cli) and not slow
    ors = " or ".join(sorted(tokens))
    return f"({ors})"
