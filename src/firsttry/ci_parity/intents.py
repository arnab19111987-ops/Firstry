from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class CommandIntent:
    """
    Represents a semantic intent for a step.

    - key: stable identifier (e.g. "lint_fast", "tests_full")
    - firsttry_cmd: preferred FirstTry-native command (may be None)
    - raw_cmd: the canonical CI command for parity/fallback
    - ecosystem: "python", "node", "go", etc. (for future use)
    """
    key: str
    firsttry_cmd: Optional[str]
    raw_cmd: str
    ecosystem: str = "python"


INTENT_REGISTRY: Dict[str, CommandIntent] = {
    # ---------- Python intents ----------
    "lint_fast": CommandIntent(
        key="lint_fast",
        firsttry_cmd="firsttry lint --fast",
        raw_cmd="ruff .",
        ecosystem="python",
    ),
    "lint_full": CommandIntent(
        key="lint_full",
        firsttry_cmd="firsttry lint --full",
        raw_cmd="ruff .",
        ecosystem="python",
    ),
    "tests_fast": CommandIntent(
        key="tests_fast",
        firsttry_cmd="firsttry pytest --fast",
        raw_cmd="pytest -q -k 'not slow and not e2e'",
        ecosystem="python",
    ),
    "tests_full": CommandIntent(
        key="tests_full",
        firsttry_cmd="firsttry pytest --full",
        raw_cmd="pytest -q",
        ecosystem="python",
    ),
    "typecheck": CommandIntent(
        key="typecheck",
        firsttry_cmd="firsttry typecheck",
        raw_cmd="mypy src/firsttry",
        ecosystem="python",
    ),
    "sbom": CommandIntent(
        key="sbom",
        firsttry_cmd="firsttry sbom --all",
        raw_cmd="python tools/gen_sbom.py",
        ecosystem="python",
    ),
    "security_audit": CommandIntent(
        key="security_audit",
        firsttry_cmd="firsttry security-audit",
        raw_cmd="bandit -r src/firsttry",
        ecosystem="python",
    ),

    # ---------- Node / JS intents ----------
    "node_tests": CommandIntent(
        key="node_tests",
        firsttry_cmd="firsttry node-tests",
        raw_cmd="npm test",
        ecosystem="node",
    ),
    "node_lint": CommandIntent(
        key="node_lint",
        firsttry_cmd="firsttry node-lint",
        raw_cmd="npm run lint",
        ecosystem="node",
    ),

    # ---------- Go intents ----------
    "go_tests": CommandIntent(
        key="go_tests",
        firsttry_cmd="firsttry go-tests",
        raw_cmd="go test ./...",
        ecosystem="go",
    ),

    # ---------- Terraform / infra ----------
    "tf_plan": CommandIntent(
        key="tf_plan",
        firsttry_cmd="firsttry tf-plan",
        raw_cmd="terraform plan -input=false",
        ecosystem="infra",
    ),
}


def get_intent(key: str) -> Optional[CommandIntent]:
    return INTENT_REGISTRY.get(key)
