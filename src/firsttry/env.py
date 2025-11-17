from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class DetectedEnv:
    has_python: bool
    has_node: bool
    has_go: bool
    python_files: int
    node_files: int
    go_files: int

    def to_pretty_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def detect_environment(root: Path) -> DetectedEnv:
    """Very lightweight repo scan.
    - Python: any *.py
    - Node: any package.json
    - Go: any *.go
    """
    # NOTE: using rglob is fine for medium repos; optimize later if needed
    python_files = list(root.rglob("*.py"))
    node_files = list(root.rglob("package.json"))
    go_files = list(root.rglob("*.go"))

    return DetectedEnv(
        has_python=bool(python_files),
        has_node=bool(node_files),
        has_go=bool(go_files),
        python_files=len(python_files),
        node_files=len(node_files),
        go_files=len(go_files),
    )
