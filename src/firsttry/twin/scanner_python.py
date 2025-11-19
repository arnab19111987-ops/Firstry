from __future__ import annotations

import ast
import tomllib
from pathlib import Path
from typing import Iterable, Optional

from .graph import CodebaseTwin, FileNode, ProjectNode
from .hashers import hash_dir, hash_file


def _iter_py_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.py"):
        if any(part.startswith(".") for part in p.parts):
            continue
        yield p


def _module_name(repo_root: Path, file_path: Path) -> Optional[str]:
    # Heuristic: turn path like src/pkg/mod.py into pkg.mod if under a src-like root
    try:
        rel = file_path.relative_to(repo_root)
    except ValueError:
        rel = file_path
    parts = list(rel.parts)
    if parts and parts[0] in {"src", "lib"}:
        parts = parts[1:]
    if not parts:
        return None
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    return ".".join(p for p in parts if p)


def _imports_from_ast(src: str) -> set[str]:
    out: set[str] = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                out.add(a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom):
            if n.module:
                out.add(n.module.split(".")[0])
    return out


def build_python_twin(repo_root: Path) -> CodebaseTwin:
    twin = CodebaseTwin(repo_root=str(repo_root))
    # 1) project-level detection via pyproject.toml (optional poetry/pep621)
    pyproject = repo_root / "pyproject.toml"
    if pyproject.exists():
        data = tomllib.loads(pyproject.read_text("utf-8"))
        name = (
            (data.get("project", {}) or {}).get("name")
            or (data.get("tool", {}).get("poetry", {}) or {}).get("name")
            or "python-project"
        )
        proj = ProjectNode(name=name, lang="python", root=".", deps=set(), files=set())
        twin.projects[proj.name] = proj

    # 2) file-level import graph
    path_to_mod: dict[str, str] = {}
    for p in _iter_py_files(repo_root):
        rel = p.relative_to(repo_root).as_posix()
        src = p.read_text("utf-8", errors="ignore")
        mod = _module_name(repo_root, p)
        imps = _imports_from_ast(src)

        fn = FileNode(path=rel, lang="py", module=mod, hash=hash_file(p), imports=imps)
        twin.files[rel] = fn
        if mod:
            path_to_mod[mod] = rel
            twin.module_to_files.setdefault(mod, set()).add(rel)
        # attach to single project if exactly one exists
        if twin.projects:
            list(twin.projects.values())[0].files.add(rel)

    # 3) resolve imports → file dependencies (best-effort)
    for f in twin.files.values():
        for imp in f.imports:
            target = path_to_mod.get(imp)
            if target:
                f.depends_on.add(target)
                twin.files[target].dependents.add(f.path)

    # 4) project hash (aggregate)
    for proj in twin.projects.values():
        files = [Path(repo_root / f) for f in proj.files]
        proj.hash = hash_dir(files) if files else None

    return twin
