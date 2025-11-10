from __future__ import annotations

from typing import Iterable


def format_unmapped_ci_jobs(missing: Iterable[str]) -> str:
    lines = ["Unmapped CI jobs detected:"]
    for k in sorted(missing):
        lines.append(f" - {k}")
    lines.append("")
    lines.append(
        "Add mappings to .firsttry/ci_mirror.toml or mark intentionally unmapped."
    )
    return "\n".join(lines)


__all__ = ["format_unmapped_ci_jobs"]
from __future__ import annotations

from typing import List

from ..ci_discovery.model import CIJob


def format_unmapped_ci_jobs(unmapped: List[CIJob]) -> str:
    if not unmapped:
        return ""

    lines = ["Unmapped CI Jobs detected:\n"]
    for j in unmapped:
        lines.append(f" - {j.workflow}:{j.job_id} ({j.job_name})")
    return "\n".join(lines) + "\n"


__all__ = ["format_unmapped_ci_jobs"]
