"""DAG planner: builds concrete task commands from project configuration.

The planner takes a twin (project config) and produces a DAG with concrete
shell commands for linting, type checking, and testing, with dependency
injection from the config.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from typing import Dict

from .model import DAG
from .model import Task


class Planner:
    """Builds a DAG from project configuration."""

    def __init__(self) -> None:
        """Initialize the planner."""
        pass

    def build_dag(self, twin_dict: Dict[str, Any], root: Path | str) -> DAG:
        """Build a DAG from a twin (project config) dictionary.

        Supported twin keys:
            pytest_cmd: List of pytest command and args
            ruff_cmd: List of ruff command and args
            mypy_cmd: List of mypy command and args
            pytest_depends_on: Set of task IDs that pytest depends on
            ruff_depends_on: Set of task IDs that ruff depends on
            mypy_depends_on: Set of task IDs that mypy depends on

        Default dependency chain:
            ruff (no deps) -> mypy (depends on ruff) -> pytest (depends on mypy)

        Args:
            twin_dict: Project configuration dictionary
            root: Project root path

        Returns:
            DAG with concrete tasks
        """
        root_path = Path(root) if isinstance(root, str) else root
        dag = DAG()

        # Extract commands from config
        ruff_cmd = twin_dict.get("ruff_cmd", ["ruff", "check", "src"])
        mypy_cmd = twin_dict.get("mypy_cmd", ["mypy", "src"])
        pytest_cmd = twin_dict.get("pytest_cmd", ["pytest", "tests"])

        # Extract custom dependencies
        ruff_deps = twin_dict.get("ruff_depends_on", set())
        mypy_deps = twin_dict.get("mypy_depends_on", {"ruff"})
        pytest_deps = twin_dict.get("pytest_depends_on", {"mypy"})

        # Create ruff task
        ruff_cache = self._compute_cache_key("ruff", ruff_cmd, root_path)
        ruff_task = Task(
            id="ruff",
            cmd=ruff_cmd,
            deps=ruff_deps,
            cache_key=ruff_cache,
            timeout_s=60,
        )
        dag.add(ruff_task)

        # Create mypy task
        mypy_cache = self._compute_cache_key("mypy", mypy_cmd, root_path)
        mypy_task = Task(
            id="mypy",
            cmd=mypy_cmd,
            deps=mypy_deps,
            cache_key=mypy_cache,
            timeout_s=120,
        )
        dag.add(mypy_task)

        # Create pytest task
        pytest_cache = self._compute_cache_key("pytest", pytest_cmd, root_path)
        pytest_task = Task(
            id="pytest",
            cmd=pytest_cmd,
            deps=pytest_deps,
            cache_key=pytest_cache,
            timeout_s=300,
            allow_fail=False,
        )
        dag.add(pytest_task)

        return dag

    @staticmethod
    def _compute_cache_key(tool: str, cmd: list[str], root: Path) -> str:
        """Compute a cache key for a task.

        Args:
            tool: Tool name (e.g., "ruff", "mypy", "pytest")
            cmd: Command and arguments
            root: Project root

        Returns:
            Cache key hash
        """
        key_str = f"{tool}:{':'.join(cmd)}:{root}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]
