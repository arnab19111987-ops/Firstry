"""Task executor with Rust fast-path and Python fallback.

Executes tasks in dependency order. Can use Rust ft_fastpath for parallel
execution or fall back to sequential Python execution.

Supports external log files to reduce report JSON size during reporting.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from typing import Any, Dict, List

from firsttry.runner import taskcache

from .model import DAG, Task

LOG_DIR = ".firsttry/logs"

# Check for Rust fast-path backend
_RUST_OK = False
try:
    import firsttry_fastpath  # noqa: F401

    _RUST_OK = True
except ImportError:
    pass


class Executor:
    """Executes a DAG of tasks with smart backend selection."""

    def __init__(
        self, dag: DAG, use_rust: bool | None = None, use_external_logs: bool = True
    ) -> None:
        """Initialize executor.

        Args:
            dag: The DAG to execute
            use_rust: Force Rust (True) or Python (False), or auto-detect (None)
            use_external_logs: If True, write task output to external files
        """
        self.dag = dag

        if use_rust is None:
            self.use_rust = _RUST_OK
        else:
            self.use_rust = use_rust and _RUST_OK

        self.use_external_logs = use_external_logs
        self.task_logs: Dict[str, Dict[str, str]] = (
            {}
        )  # task_id -> {"stdout": path, "stderr": path}

    def execute(self) -> Dict[str, int]:
        """Execute all tasks in topological order.

        Returns:
            Dictionary mapping task ID to exit code (0 = success)
        """
        if self.use_external_logs:
            os.makedirs(LOG_DIR, exist_ok=True)

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
            meta = self._run_task(task)
            exit_code = meta.get("code", 1)
            results[task_id] = exit_code

            # Stop on failure if allow_fail is False
            if exit_code != 0 and not task.allow_fail:
                print(f"[executor] Task {task_id} failed with code {exit_code}", file=sys.stderr)
                break

        return results

    def _run_task(self, task: Task) -> Dict[str, Any]:
        """Run a single task.

        Args:
            task: The task to run

        Returns:
            Dict with id, cmd, code, duration_s, and optional log paths
        """
        import time

        # Try task cache first
        ckey = taskcache.key_for(task.id, task.cmd, self._inputs_for(task), self._salt_for(task))
        cached = taskcache.get(task.id, ckey)
        if cached is not None:
            cached = dict(cached)
            cached["cache"] = "hit"
            print(f"[executor] Cache hit {task.id}: {' '.join(task.cmd)}", file=sys.stderr)
            return cached

        print(f"[executor] Running {task.id}: {' '.join(task.cmd)}", file=sys.stderr)

        start_time = time.time()
        # Prepare stdout/stderr redirection
        stdout_file = None
        stderr_file = None
        stdout_path = None
        stderr_path = None
        exit_code = 1

        try:
            if self.use_external_logs:
                # Create unique log files per task
                task_log_id = f"{task.id}_{uuid.uuid4().hex[:8]}"
                stdout_path = os.path.join(LOG_DIR, f"{task_log_id}.out")
                stderr_path = os.path.join(LOG_DIR, f"{task_log_id}.err")

                stdout_file = open(stdout_path, "w")
                stderr_file = open(stderr_path, "w")

                self.task_logs[task.id] = {"stdout": stdout_path, "stderr": stderr_path}

                result = subprocess.run(
                    task.cmd,
                    timeout=task.timeout_s if task.timeout_s > 0 else None,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    check=False,
                )
                exit_code = result.returncode
            else:
                # Run with output to stdout/stderr
                result = subprocess.run(
                    task.cmd,
                    timeout=task.timeout_s if task.timeout_s > 0 else None,
                    check=False,
                )
                exit_code = result.returncode

        except subprocess.TimeoutExpired:
            print(f"[executor] Task {task.id} timed out after {task.timeout_s}s", file=sys.stderr)
            exit_code = 124  # Standard timeout exit code
        except Exception as e:
            print(f"[executor] Task {task.id} failed with exception: {e}", file=sys.stderr)
            exit_code = 1
        finally:
            if stdout_file:
                stdout_file.close()
            if stderr_file:
                stderr_file.close()

        duration = time.time() - start_time

        # Build result metadata with proof
        meta: Dict[str, Any] = {
            "id": task.id,
            "cmd": task.cmd,
            "code": exit_code,
            "duration_s": round(duration, 3),
        }
        if self.use_external_logs and stdout_path and stderr_path:
            meta.update({"stdout_path": stdout_path, "stderr_path": stderr_path})

        # Cache successful results
        if exit_code == 0:
            cache_payload = {k: v for k, v in meta.items() if k not in ("duration_s", "cache")}
            taskcache.put(task.id, ckey, cache_payload)

        meta["cache"] = "miss"
        return meta

    def _inputs_for(self, task: Task) -> list[str]:
        """Determine input files that affect task output.

        Args:
            task: Task to analyze

        Returns:
            List of file/directory paths
        """
        if task.id == "ruff":
            return ["src"]
        if task.id == "mypy":
            return ["src", "pyproject.toml"]
        if task.id == "pytest":
            return ["src", "tests", "pyproject.toml"]
        return ["src", "tests"]

    def _salt_for(self, task: Task) -> dict:
        """Generate salt for task cache key.

        Args:
            task: Task to analyze

        Returns:
            Dict of metadata affecting task output
        """
        return {
            "timeout": task.timeout_s,
            "firsttry_version": os.environ.get("FIRSTTRY_VERSION", "1"),
        }
