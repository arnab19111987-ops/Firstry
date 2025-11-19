from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class FileNode:
    path: str  # repo-relative
    lang: str  # "py", "js", "ts", etc.
    module: Optional[str] = None
    hash: Optional[str] = None
    imports: Set[str] = field(default_factory=set)  # import targets (module names)
    depends_on: Set[str] = field(default_factory=set)  # file paths (resolved)
    dependents: Set[str] = field(default_factory=set)  # reverse edges


@dataclass
class ProjectNode:
    name: str
    lang: str  # "python", "node"
    root: str  # repo-relative directory
    deps: Set[str] = field(default_factory=set)  # other ProjectNode names
    files: Set[str] = field(default_factory=set)  # repo-relative file paths
    hash: Optional[str] = None  # aggregate hash


@dataclass
class CodebaseTwin:
    repo_root: str
    files: Dict[str, FileNode] = field(default_factory=dict)  # by path
    projects: Dict[str, ProjectNode] = field(default_factory=dict)  # by project name
    # index helpers
    module_to_files: Dict[str, Set[str]] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "repo_root": self.repo_root,
                "files": {k: self._file_to_dict(v) for k, v in self.files.items()},
                "projects": {
                    k: self._proj_to_dict(v) for k, v in self.projects.items()
                },
                "module_to_files": {
                    k: list(v) for k, v in self.module_to_files.items()
                },
            },
            separators=(",", ":"),
            ensure_ascii=False,
        )

    @staticmethod
    def _file_to_dict(f: FileNode) -> dict:
        return {
            "path": f.path,
            "lang": f.lang,
            "module": f.module,
            "hash": f.hash,
            "imports": sorted(f.imports),
            "depends_on": sorted(f.depends_on),
            "dependents": sorted(f.dependents),
        }

    @staticmethod
    def _proj_to_dict(p: ProjectNode) -> dict:
        return {
            "name": p.name,
            "lang": p.lang,
            "root": p.root,
            "deps": sorted(p.deps),
            "files": sorted(p.files),
            "hash": p.hash,
        }

    @classmethod
    def from_json(cls, s: str) -> CodebaseTwin:
        o = json.loads(s)
        twin = cls(repo_root=o["repo_root"])
        for path, fd in o["files"].items():
            twin.files[path] = FileNode(
                path=fd["path"],
                lang=fd["lang"],
                module=fd.get("module"),
                hash=fd.get("hash"),
                imports=set(fd.get("imports", [])),
                depends_on=set(fd.get("depends_on", [])),
                dependents=set(fd.get("dependents", [])),
            )
        for name, pd in o["projects"].items():
            twin.projects[name] = ProjectNode(
                name=pd["name"],
                lang=pd["lang"],
                root=pd["root"],
                deps=set(pd.get("deps", [])),
                files=set(pd.get("files", [])),
                hash=pd.get("hash"),
            )
        twin.module_to_files = {
            k: set(v) for k, v in o.get("module_to_files", {}).items()
        }
        return twin

    # ----- Impact analysis -----
    def impacted_files(self, changed_paths: List[str]) -> Set[str]:
        """Return transitive closure of dependents for changed files."""
        q = list(changed_paths)
        seen = set(q)
        while q:
            cur = q.pop()
            node = self.files.get(cur)
            if not node:
                continue
            for dep in node.dependents:
                if dep not in seen:
                    seen.add(dep)
                    q.append(dep)
        return seen

    def project_of_file(self, path: str) -> Optional[str]:
        for name, proj in self.projects.items():
            if path in proj.files:
                return name
        return None
