# src/firsttry/agent_manager.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

MAX_AGENTS = 12

FAMILY_WEIGHTS = {
    "lint": 3,
    "tests": 3,
    "type": 2,
    "security": 1,
    "deps": 1,
    "ci_parity": 1,
    "custom": 1,
}


@dataclass
class MachineFacts:
    cpus: int
    ram_mb: Optional[int] = None


@dataclass
class RepoFacts:
    file_count: int
    test_count: int
    languages: List[str]


class SmartAgentManager:
    def __init__(self, machine: MachineFacts, repo: RepoFacts):
        self.machine = machine
        self.repo = repo

    @classmethod
    def from_context(
        cls, context: Dict[str, Any], repo_profile: Dict[str, Any]
    ) -> "SmartAgentManager":
        cpus = int(context.get("machine", {}).get("cpus", 4))
        file_count = int(repo_profile.get("file_count", 80))
        test_count = int(repo_profile.get("test_count", 0))
        languages = (
            repo_profile.get("languages") or context.get("languages") or ["python"]
        )
        return cls(
            machine=MachineFacts(cpus=cpus),
            repo=RepoFacts(
                file_count=file_count, test_count=test_count, languages=languages
            ),
        )

    def _compute_budget(self) -> int:
        base = min(2 * self.machine.cpus, MAX_AGENTS)
        if self.repo.file_count > 600:
            base = min(base + 2, MAX_AGENTS)
        return max(base, 2)

    def allocate_for_plan(self, plan: List[Dict[str, Any]]) -> Dict[str, int]:
        budget = self._compute_budget()

        families: List[str] = []
        for item in plan:
            fam = item["family"]
            if fam not in families:
                families.append(fam)

        # 1) ensure 1 per family
        alloc: Dict[str, int] = {fam: 1 for fam in families}
        budget_left = budget - len(families)
        if budget_left <= 0:
            return alloc

        # 2) distribute by weight
        total_weight = sum(FAMILY_WEIGHTS.get(f, 1) for f in families) or 1
        for fam in families:
            if budget_left <= 0:
                break
            weight = FAMILY_WEIGHTS.get(fam, 1)
            extra = (weight * budget_left) // total_weight
            if extra > 0:
                alloc[fam] += extra

        # 3) shrink if over
        total_alloc = sum(alloc.values())
        while total_alloc > budget:
            # drop from lowest weight but not below 1
            low = sorted(families, key=lambda f: FAMILY_WEIGHTS.get(f, 1))
            for fam in low:
                if alloc[fam] > 1 and total_alloc > budget:
                    alloc[fam] -= 1
                    total_alloc -= 1
        return alloc
