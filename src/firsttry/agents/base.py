# src/firsttry/agents/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentResult:
    name: str
    ok: bool
    duration_ms: int = 0
    issues: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


class Agent(ABC):
    name: str = "agent"

    @abstractmethod
    async def run(self, ctx: Any) -> AgentResult:
        raise NotImplementedError
