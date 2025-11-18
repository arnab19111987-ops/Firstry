from __future__ import annotations

from typing import Iterable


def format_unmapped_ci_jobs(missing: Iterable[str]) -> str:
    lines = ["Unmapped CI jobs detected:"]
    for k in sorted(missing):
        lines.append(f" - {k}")
    lines.append("")
    lines.append("Add mappings to .firsttry/ci_mirror.toml or mark intentionally unmapped.")
    return "\n".join(lines)


__all__ = ["format_unmapped_ci_jobs"]
