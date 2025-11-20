from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from ..twin.graph import CodebaseTwin


@dataclass
class Task:
    id: str  # e.g., "ruff:api", "pytest:app"
    check_id: str  # e.g., "ruff", "pytest", "npm-lint"
    targets: List[str]  # intent: project root(s) or precise file lists
    flags: List[str]
    deps: Set[str] = field(default_factory=set)


@dataclass
class Plan:
    tasks: Dict[str, Task] = field(default_factory=dict)


def _project_files(twin: CodebaseTwin, proj: str) -> Set[str]:
    p = twin.projects.get(proj)
    return set(p.files) if p else set()


def _project_root(twin: CodebaseTwin, proj: str) -> str:
    p = twin.projects.get(proj)
    return p.root if p and p.root else "."


def _group_impacted_by_project(
    twin: CodebaseTwin, changed: List[str]
) -> Dict[str, Set[str]]:
    impacted = twin.impacted_files(changed) if changed else set(twin.files.keys())
    out: Dict[str, Set[str]] = {}
    for f in impacted:
        proj = twin.project_of_file(f) or "_root"
        out.setdefault(proj, set()).add(f)
    return out


def build_plan_from_twin(
    twin: CodebaseTwin,
    *,
    tier: str,
    changed: List[str],
    workflow_requires: List[str] | None = None,
    pytest_shards: int = 1,
) -> Plan:
    """
    Polyglot planning:
      - Iterate projects from the twin
      - Add language-appropriate tasks
      - Scope targets to project roots (or narrowed files if you want later)
      - Add DAG deps from workflow policy
    """
    workflow_requires = workflow_requires or []
    per_proj_impacted = _group_impacted_by_project(twin, changed)

    plan = Plan()

    def add(task: Task):
        plan.tasks[task.id] = task

    for proj_name, files in per_proj_impacted.items():
        lang = (
            twin.projects.get(proj_name).lang
            if proj_name in twin.projects
            else "python"
        )
        root = _project_root(twin, proj_name)

        if lang == "python":
            py_changed = any(f.endswith(".py") for f in files) or proj_name == "_root"
            test_targets = sorted(
                [f for f in files if f.startswith("tests/") or "/tests/" in f]
            )

            if py_changed:
                ruff_id = f"ruff:{proj_name}"
                add(Task(id=ruff_id, check_id="ruff", targets=[root], flags=[]))

                # Typing checks can be slow and noisy for repos with typing debt.
                # Only include `mypy` in stricter tiers (e.g. `strict`, `pro`).
                if tier in {"pro", "promax", "strict", "enterprise"}:
                    mypy_id = f"mypy:{proj_name}"
                    add(Task(id=mypy_id, check_id="mypy", targets=[root], flags=[]))

                # pytest depends on ruff/mypy if configured
                deps = {
                    f"{d}:{proj_name}"
                    for d in workflow_requires
                    if d in {"ruff", "mypy"}
                }
                pt_id = f"pytest:{proj_name}"
                add(
                    Task(
                        id=pt_id,
                        check_id="pytest",
                        targets=test_targets or [root],
                        flags=["-q"],
                        deps=deps,
                    )
                )

            if tier in {"pro", "promax"}:
                # security task (example)
                b_id = f"bandit:{proj_name}"
                add(Task(id=b_id, check_id="bandit", targets=[root], flags=[]))

        elif lang == "node":
            js_changed = (
                any(
                    f.endswith(suf)
                    for f in files
                    for suf in (".js", ".jsx", ".ts", ".tsx")
                )
                or proj_name == "_root"
            )
            if js_changed:
                lint_id = f"npm-lint:{proj_name}"
                test_id = f"npm-test:{proj_name}"
                add(Task(id=lint_id, check_id="npm-lint", targets=[root], flags=[]))
                deps = {
                    f"{d}:{proj_name}" for d in workflow_requires if d in {"npm-lint"}
                }
                add(
                    Task(
                        id=test_id,
                        check_id="npm-test",
                        targets=[root],
                        flags=[],
                        deps=deps,
                    )
                )

        else:
            # Future: go, rust, etc. Hook here
            pass

    return plan
