from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from firsttry.planner.dag import Plan, build_plan_from_twin


@dataclass
class FakeProject:
    name: str
    lang: str = "python"
    root: Path | None = None


@dataclass
class FakeTwin:
    projects: Dict[str, FakeProject]
    impacted: Dict[str, List[str]]


def fake_build_plan(workflow_requires: dict[str, list[str]]) -> Plan:
    """
    Build a very small plan with a single Python project and a few files,
    injecting workflow_requires into build_plan_from_twin.
    """
    proj = FakeProject(name="proj-a", lang="python")
    twin = FakeTwin(
        projects={"proj-a": proj},
        impacted={"proj-a": ["proj_a/foo.py", "proj_a/test_foo.py"]},
    )

    plan = build_plan_from_twin(
        twin,  # type: ignore[arg-type]
        tier="free-lite",
        changed=["proj_a/foo.py", "proj_a/test_foo.py"],
        workflow_requires=workflow_requires,
    )
    return plan


def test_workflow_requires_set_deps_on_tasks():
    workflow_requires = {"pytest": ["ruff", "mypy"], "mypy": ["ruff"]}

    plan = fake_build_plan(workflow_requires)

    # Index tasks by check_id for easier assertions
    tasks_by_check = {}
    for task in plan.tasks.values():
        tasks_by_check.setdefault(task.check_id, []).append(task)

    # pytest tasks should depend on ruff and mypy for proj-a
    pytest_tasks = tasks_by_check.get("pytest") or []
    assert pytest_tasks, "Expected at least one pytest task in plan"
    for t in pytest_tasks:
        assert "ruff:proj-a" in t.deps
        assert "mypy:proj-a" in t.deps

    # mypy tasks should depend on ruff:proj-a
    mypy_tasks = tasks_by_check.get("mypy") or []
    for t in mypy_tasks:
        assert "ruff:proj-a" in t.deps
