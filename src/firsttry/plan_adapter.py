from __future__ import annotations
from typing import Any, Dict, List

# Simple adapter from planner steps -> orchestrator items (family/tool)
TOOL_MAP = {
    # planner step id -> (family, tool)
    # extend this mapping for your pipelines
    "py-lint": ("python", "ruff"),
    "py-type": ("python", "mypy"),
    "py-test": ("python", "pytest"),
    "py-security": ("python", "bandit"),
    "js-lint": ("node", "eslint"),
    "js-test": ("node", "npm-test"),
    # additional pipeline steps
    "py-coverage": ("python", "pytest"),
    "js-type": ("node", "tsc"),
    "go-lint": ("go", "golangci-lint"),
    "go-test": ("go", "go-test"),
    "rs-lint": ("rust", "cargo-clippy"),
    "rs-test": ("rust", "cargo-test"),
    "docker-lint": ("infra", "hadolint"),
    "tf-lint": ("infra", "tflint"),
}


def adapt_planner_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in steps:
        key = s.get("id") or s.get("kind")
        fam, tool = TOOL_MAP.get(key, (s.get("lang"), s.get("tool")))
        item = {
            "id": s.get("id") or s.get("name"),
            "family": fam or (s.get("lang") or "misc"),
            "tool": tool or s.get("tool"),
            "paths": s.get("paths") or [],
            "cmd": s.get("cmd"),
            "args": s.get("args") or [],
            "timeout": s.get("timeout"),
            "mutating": bool(s.get("autofix", False)),
        }
        out.append(item)
    return out
