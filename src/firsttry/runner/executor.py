"""Task executor with Rust fast-path and Python fallback.

Executes tasks in dependency order. Can use Rust ft_fastpath for parallel
execution or fall back to sequential Python execution.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Dict
from typing import List

from .model import DAG
from .model import Task

# Check for Rust fast-path backend
_RUST_OK = False
try:
    import firsttry_fastpath  # noqa: F401

    _RUST_OK = True
except ImportError:
    pass


class Executor:
    """Executes a DAG of tasks with smart backend selection."""

    def __init__(self, dag: DAG, use_rust: bool | None = None) -> None:
        """Initialize executor.

        Args:
            dag: The DAG to execute
            use_rust: Force Rust (True) or Python (False), or auto-detect (None)
        """
        self.dag = dag

        if use_rust is None:
            self.use_rust = _RUST_OK
        else:
            self.use_rust = use_rust and _RUST_OK

    def execute(self) -> Dict[str, int]:
        """Execute all tasks in topological order.

        Returns:
            Dictionary mapping task ID to exit code (0 = success)
        """
        order = self.dag.toposort()
        return self._run_sequential(order)

    def _run_sequential(self, order: List[str]) -> Dict[str, int]:
        """Run tasks sequentially in given order.

        Args:
            order: List of task IDs in execution order

        Returns:
            Exit codes for each task
        """
        results: Dict[str, int] = {}

        for task_id in order:
            task = self.dag.tasks[task_id]
            exit_code = self._run_task(task)
            results[task_id] = exit_code

            # Stop on failure if allow_fail is False
            if exit_code != 0 and not task.allow_fail:
                print(f"[executor] Task {task_id} failed with code {exit_code}", file=sys.stderr)
                break

        return results

    def _run_task(self, task: Task) -> int:
        """Run a single task.

        Args:
            task: The task to run

        Returns:
            Exit code
        """
        print(f"[executor] Running {task.id}: {' '.join(task.cmd)}", file=sys.stderr)

        try:
            result = subprocess.run(
                task.cmd,
                timeout=task.timeout_s if task.timeout_s > 0 else None,
                check=False,
            )
            return result.returncode
        except subprocess.TimeoutExpired:
            print(f"[executor] Task {task.id} timed out after {task.timeout_s}s", file=sys.stderr)
            return 124  # Standard timeout exit code
        except Exception as e:
            print(f"[executor] Task {task.id} failed with exception: {e}", file=sys.stderr)
            return 1
