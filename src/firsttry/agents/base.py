# src/firsttry/agents/base.py
from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass
class AgentResult:
    name: str
    ok: bool
    duration_ms: int = 0
    issues: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class Agent(ABC):
    name: str = "agent"

    @abstractmethod
    async def run(self, ctx: Any) -> AgentResult:
        raise NotImplementedError
