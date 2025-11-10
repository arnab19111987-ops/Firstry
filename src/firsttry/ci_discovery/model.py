from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class CIJob:
    workflow: str
    job_id: str
    job_name: str
    uses_actions: bool = False
    run_commands: List[str] = field(default_factory=list)


__all__ = ["CIJob"]
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class CIJob:
    workflow: str
    job_id: str
    job_name: str
    uses_actions: List[str]
    run_commands: List[str]


__all__ = ["CIJob"]
