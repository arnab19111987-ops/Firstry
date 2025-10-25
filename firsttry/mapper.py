from __future__ import annotations

import pathlib
import typing as t


def guess_test_kexpr(changed_paths: t.Iterable[str]) -> str:
    """
    Heuristic: convert changed file paths into a pytest -k expression.

    - For each changed .py file, take the stem ("foo" from foo.py)
      and its parent directory ("auth" from auth/foo.py).
    - Dedupe, sort, and join them with " or " so pytest can target
      likely-related tests.

    If no interesting tokens, return "" (means: run full suite).
    """
    tokens: list[str] = []

    for p in changed_paths:
        if not p.endswith(".py"):
            continue

        stem = pathlib.Path(p).stem
        if stem and stem not in tokens:
            tokens.append(stem)

        parent = pathlib.Path(p).parent.name
        if parent and parent not in tokens:
            tokens.append(parent)

    if not tokens:
        return ""

    tokens_sorted = sorted(tokens)
    return " or ".join(tokens_sorted)
