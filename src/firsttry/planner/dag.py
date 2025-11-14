from __future__ import annotations

import json
import os
from dataclasses import dataclass
from dataclasses import field
from typing import FrozenSet
from typing import Iterable
from typing import Mapping
from typing import Optional

from ..twin.graph import CodebaseTwin

# --- Team Intel hook (top-level export) ---
try:
    from ..license_guard import get_current_tier
except Exception:

    def get_current_tier() -> str:
        return "free-lite"


def _get_flaky_test_list_from_ci() -> list[str]:
    try:
        path = os.getenv("FT_FLAKY_FILE", ".firsttry/flaky_tests.json")
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("tests") if isinstance(data, dict) else data
        return [str(x) for x in (items or [])]
    except Exception:
        return []


def _add_tests_to_plan(plan, nodeids: list[str]) -> None:
    if not nodeids:
        return
    add = getattr(plan, "add_tests", None) or getattr(plan, "include_tests", None)
    if callable(add):
        add(nodeids)


def maybe_apply_team_intel(plan) -> None:
    """
    Call this after constructing the base plan.
    Pro: sync & include flaky list.
    Free: print friendly upsell, no-op.
    """
    if get_current_tier() == "pro":
        print("🌐 Pro: Syncing team's flaky test list…")
        _add_tests_to_plan(plan, _get_flaky_test_list_from_ci())
    else:
        print("🔒 Pro Feature Skipped: Auto-run known flaky tests from CI.")
        print("   (Upgrade at firsttry.io to sync with your team)")


@dataclass(frozen=True)
class Task:
    """Single DAG node representing one check/run.

    Immutable "sealed envelope" passed to the executor.
    """

    id: str
    check_id: str
    targets: list[str]
    flags: list[str]
    deps: FrozenSet[str] = field(default_factory=frozenset)
    timeout_s: Optional[int] = None  # None = use global/default timeout


@dataclass
class Plan:
    tasks: dict[str, Task] = field(default_factory=dict)


def _project_files(twin: CodebaseTwin, proj: str) -> set[str]:
    p = twin.projects.get(proj)
    return set(p.files) if p else set()


def _project_root(twin: CodebaseTwin, proj: str) -> str:
    p = twin.projects.get(proj)
    return p.root if p and p.root else "."


def _group_impacted_by_project(
    twin: CodebaseTwin,
    changed: list[str],
) -> dict[str, set[str]]:
    # Support multiple twin shapes used across tests and code:
    # - twin.impacted_files(changed) -> iterable of file paths
    # - twin.impacted -> mapping proj -> list[str]
    # - twin.files -> mapping file -> metadata
    out: dict[str, set[str]] = {}
    if hasattr(twin, "impacted_files") and callable(getattr(twin, "impacted_files")):
        impacted = twin.impacted_files(changed) if changed else set(twin.files.keys())
        out = {}
        for f in impacted:
            proj = getattr(twin, "project_of_file", lambda _f: "_root")(f) or "_root"
            out.setdefault(proj, set()).add(f)
        return out

    # If twin exposes an 'impacted' mapping (tests use this), mirror it
    if hasattr(twin, "impacted") and isinstance(getattr(twin, "impacted"), dict):
        raw = getattr(twin, "impacted")
        out = {}
        for proj, files in raw.items():
            out[proj] = set(files or [])
        return out

    # Fallback: try twin.files mapping
    if hasattr(twin, "files") and isinstance(getattr(twin, "files"), dict):
        return {"_root": set(getattr(twin, "files").keys())}

    return {}


def _deps_for_check(
    check_id: str,
    proj_name: str,
    workflow_requires: Mapping[str, Iterable[str]] | None,
) -> set[str]:
    """
    Convert workflow_requires mapping into fully-qualified Task deps for a
    given check and project name (e.g. 'ruff:proj-a').
    """
    if not workflow_requires:
        return set()
    requires = workflow_requires.get(check_id) or []
    return {f"{dep}:{proj_name}" for dep in requires}


def build_plan_from_twin(
    twin: CodebaseTwin,
    *,
    tier: str,
    changed: list[str],
    workflow_requires: Mapping[str, Iterable[str]] | None = None,
    pytest_shards: int = 1,
) -> Plan:
    """Polyglot planning:
    - Iterate projects from the twin
    - Add language-appropriate tasks
    - Scope targets to project roots (or narrowed files if you want later)
    - Add DAG deps from workflow policy
    """
    # Normalize workflow_requires to a mapping from check_id -> iterable deps
    workflow_requires = workflow_requires or {}
    per_proj_impacted = _group_impacted_by_project(twin, changed)

    plan = Plan()

    def add(task: Task):
        plan.tasks[task.id] = task

    for proj_name, files in per_proj_impacted.items():
        proj = twin.projects.get(proj_name)
        lang = proj.lang if proj else "python"
        root = _project_root(twin, proj_name)

        if lang == "python":
            py_changed = any(f.endswith(".py") for f in files) or proj_name == "_root"
            test_targets = sorted([f for f in files if f.startswith("tests/") or "/tests/" in f])

            if py_changed:
                ruff_id = f"ruff:{proj_name}"
                mypy_id = f"mypy:{proj_name}"
                add(
                    Task(
                        id=ruff_id,
                        check_id="ruff",
                        targets=[root],
                        flags=[],
                        deps=frozenset(_deps_for_check("ruff", proj_name, workflow_requires)),
                        timeout_s=None,
                    )
                )
                add(
                    Task(
                        id=mypy_id,
                        check_id="mypy",
                        targets=[root],
                        flags=[],
                        deps=frozenset(_deps_for_check("mypy", proj_name, workflow_requires)),
                        timeout_s=None,
                    )
                )

                # pytest depends on configured workflow requirements
                deps = frozenset(_deps_for_check("pytest", proj_name, workflow_requires))
                pt_id = f"pytest:{proj_name}"
                add(
                    Task(
                        id=pt_id,
                        check_id="pytest",
                        targets=test_targets or [root],
                        flags=["-q"],
                        deps=deps,
                        timeout_s=None,
                    )
                )

            if tier in {"pro", "promax"}:
                # security task (example)
                b_id = f"bandit:{proj_name}"
                add(
                    Task(
                        id=b_id,
                        check_id="bandit",
                        targets=[root],
                        flags=[],
                        deps=frozenset(),
                        timeout_s=None,
                    )
                )

        elif lang == "node":
            js_changed = (
                any(f.endswith(suf) for f in files for suf in (".js", ".jsx", ".ts", ".tsx"))
                or proj_name == "_root"
            )
            if js_changed:
                lint_id = f"npm-lint:{proj_name}"
                test_id = f"npm-test:{proj_name}"
                add(
                    Task(
                        id=lint_id,
                        check_id="npm-lint",
                        targets=[root],
                        flags=[],
                        deps=frozenset(_deps_for_check("npm-lint", proj_name, workflow_requires)),
                        timeout_s=None,
                    )
                )
                deps = frozenset(_deps_for_check("npm-test", proj_name, workflow_requires))
                add(
                    Task(
                        id=test_id,
                        check_id="npm-test",
                        targets=[root],
                        flags=[],
                        deps=deps,
                        timeout_s=None,
                    )
                )

        else:
            # Future: go, rust, etc. Hook here
            pass

    # Team-intel helper: best-effort, non-fatal
    try:
        import json
        import os

        from firsttry.license_guard import maybe_include_flaky_tests

        from ..license_guard import get_current_tier
    except Exception:
        # Fallbacks if license helpers are not available
        import json
        import os

        def get_current_tier() -> str:
            return "free-lite"

    def _get_flaky_test_list_from_ci() -> list[str]:
        try:
            path = os.getenv("FT_FLAKY_FILE", ".firsttry/flaky_tests.json")
            if not os.path.exists(path):
                return []
            data = json.loads(open(path, "r", encoding="utf-8").read())
            items = data.get("tests") if isinstance(data, dict) else data
            return [str(x) for x in (items or [])]
        except Exception:
            return []

    def _add_tests_to_plan(plan, nodeids: list[str]) -> None:
        add = getattr(plan, "add_tests", None) or getattr(plan, "include_tests", None)
        if callable(add) and nodeids:
            add(nodeids)

    def maybe_apply_team_intel(plan) -> None:
        if get_current_tier() == "pro":
            print("🌐 Pro: Syncing team's flaky test list…")
            _add_tests_to_plan(plan, _get_flaky_test_list_from_ci())
        else:
            print("🔒 Pro Feature Skipped: Auto-run known flaky tests from CI.")
            print("   (Upgrade at firsttry.io to sync with your team)")

    # Apply team intelligence (non-fatal)
    try:
        maybe_apply_team_intel(plan)
    except Exception:
        pass

    try:
        # Since Task is frozen, replace pytest tasks with updated targets
        for tid, t in list(plan.tasks.items()):
            if getattr(t, "check_id", None) == "pytest":
                try:
                    new_targets = list(maybe_include_flaky_tests(t.targets))
                except Exception:
                    new_targets = list(t.targets)
                new_t = Task(
                    id=t.id,
                    check_id=t.check_id,
                    targets=new_targets,
                    flags=list(t.flags),
                    deps=frozenset(t.deps),
                    timeout_s=getattr(t, "timeout_s", None),
                )
                plan.tasks[tid] = new_t
    except Exception:
        # best-effort: never allow license helpers to break planning
        pass

    return plan
