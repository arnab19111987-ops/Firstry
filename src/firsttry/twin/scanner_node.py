from __future__ import annotations
from pathlib import Path
import json
from .graph import CodebaseTwin, ProjectNode

def attach_node_projects(repo_root: Path, twin: CodebaseTwin) -> None:
    pkg = repo_root / "package.json"
    if not pkg.exists():
        return
    data = json.loads(pkg.read_text())
    name = data.get("name", "node-project")
    proj = ProjectNode(name=name, lang="node", root=".", deps=set(), files=set())
    # (optionally glob js/ts files and append)
    twin.projects[name] = proj
