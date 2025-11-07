"""DAG planner: builds concrete task commands from project configuration.

The planner takes a twin (project config) and produces a DAG with concrete
shell commands for linting, type checking, and testing, with dependency
injection from the config.

Also provides plan-level caching using BLAKE2b config hashing to avoid
rebuilding the DAG on every cold start.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import List

from .model import DAG
from .model import Task

PLAN_CACHE_DIR = ".firsttry/cache"
PLAN_CACHE_PREFIX = "plan_"
FIRSTTRY_VERSION = os.environ.get("FIRSTTRY_VERSION", "1")


def _hash_bytes(b: bytes) -> str:
    """Fast 128-bit BLAKE2b hash."""
    h = hashlib.blake2b(digest_size=16)
    h.update(b)
    return h.hexdigest()


def _load_config_bytes(config_path: str) -> bytes:
    """Load config and salt with Python + FirstTry version for invalidation."""
    with open(config_path, "rb") as f:
        raw = f.read()
    # Include interpreter version and FirstTry version to invalidate on upgrades
    salt = f"\nPY:{sys.version}\nFT:{FIRSTTRY_VERSION}\n".encode()
    return raw + salt


def _plan_cache_key(config_bytes: bytes) -> str:
    """Deterministic cache key from config + versions."""
    return _hash_bytes(config_bytes)


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
        mypy_deps = twin_dict.get(
            "mypy_depends_on", set()
        )  # No dependency on ruff; both run in parallel
        pytest_deps = twin_dict.get("pytest_depends_on", {"ruff", "mypy"})  # Depends on both

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

    def get_cached_dag(self, config_path: str, twin_dict: Dict[str, Any], root: Path | str) -> DAG:
        """Build a DAG with caching based on config content hash.

        If a cached DAG exists for this config+versions, deserialize and return it.
        Otherwise, build the DAG normally and cache for next time.

        Args:
            config_path: Path to config file (e.g., "firsttry.toml")
            twin_dict: Project configuration dictionary
            root: Project root path

        Returns:
            DAG with concrete tasks
        """
        os.makedirs(PLAN_CACHE_DIR, exist_ok=True)

        cfg_bytes = _load_config_bytes(config_path)
        key = _plan_cache_key(cfg_bytes)
        cache_file = os.path.join(PLAN_CACHE_DIR, f"{PLAN_CACHE_PREFIX}{key}.json")

        # Try cache first
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "rb") as f:
                    cached_data = json.loads(f.read().decode("utf-8"))
                    # Reconstruct DAG from cached representation
                    dag = DAG()
                    for task_dict in cached_data:
                        task = Task(
                            id=task_dict["id"],
                            cmd=task_dict["cmd"],
                            deps=set(task_dict["deps"]),
                            cache_key=task_dict.get("cache_key", ""),
                            timeout_s=task_dict.get("timeout_s", 0),
                            allow_fail=task_dict.get("allow_fail", True),
                        )
                        dag.add(task)
                    return dag
            except Exception:
                # Corrupt cache—rebuild
                pass

        # Cache miss: build DAG normally
        dag = self.build_dag(twin_dict, root)

        # Serialize and cache
        try:
            cached_data = [
                {
                    "id": t.id,
                    "cmd": t.cmd,
                    "deps": sorted(t.deps),
                    "cache_key": t.cache_key,
                    "timeout_s": t.timeout_s,
                    "allow_fail": t.allow_fail,
                }
                for t in dag.tasks.values()
            ]
            with open(cache_file, "wb") as f:
                f.write(
                    json.dumps(cached_data, separators=(",", ":"), ensure_ascii=False).encode(
                        "utf-8"
                    )
                )
        except Exception:
            # If cache write fails, still return DAG
            pass

        return dag


def _compute_levels(dag: DAG) -> List[List[str]]:
    """Compute leveled (Kahn) ordering as list of levels (each level is list of task ids).

    This groups tasks that have the same depth (no inter-dependencies) so they can
    be executed in parallel within each level.
    """
    # Build in-degree map and adjacency list
    indeg = {tid: 0 for tid in dag.tasks}
    adj = {tid: [] for tid in dag.tasks}
    for a, b in dag.edges:
        if a not in dag.tasks or b not in dag.tasks:
            continue
        indeg[b] += 1
        adj[a].append(b)

    levels: List[List[str]] = []
    # Collect nodes with indeg 0
    ready = [tid for tid, d in indeg.items() if d == 0]
    while ready:
        levels.append(list(ready))
        next_ready: List[str] = []
        for n in ready:
            for nb in adj[n]:
                indeg[nb] -= 1
                if indeg[nb] == 0:
                    next_ready.append(nb)
        ready = next_ready

    # Sanity check for cycles
    processed = sum(len(lvl) for lvl in levels)
    if processed != len(dag.tasks):
        raise ValueError("Cycle detected while computing levels")

    return levels


def plan_levels_cached(config_path: str, graph_supplier: Callable[[], DAG]) -> List[List[str]]:
    """Return DAG execution levels, using plan cache if available.

    The graph_supplier is only called on cache miss and should return a ready-to-use DAG.
    """
    os.makedirs(PLAN_CACHE_DIR, exist_ok=True)

    try:
        cfg_bytes = _load_config_bytes(config_path)
    except Exception:
        # If config can't be read, fall back to supplier
        dag = graph_supplier()
        return _compute_levels(dag)

    key = _plan_cache_key(cfg_bytes)
    cache_file = os.path.join(PLAN_CACHE_DIR, f"{PLAN_CACHE_PREFIX}{key}.json")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as f:
                cached_data = json.loads(f.read().decode("utf-8"))
                dag = DAG()
                for task_dict in cached_data:
                    task = Task(
                        id=task_dict["id"],
                        cmd=task_dict["cmd"],
                        deps=set(task_dict["deps"]),
                        cache_key=task_dict.get("cache_key", ""),
                        timeout_s=task_dict.get("timeout_s", 0),
                        allow_fail=task_dict.get("allow_fail", True),
                    )
                    dag.add(task)
                return _compute_levels(dag)
        except Exception:
            # Cache corrupt — fall through to rebuild
            pass

    # Cache miss: build using supplier and write cache
    dag = graph_supplier()
    try:
        cached_data = [
            {
                "id": t.id,
                "cmd": t.cmd,
                "deps": sorted(t.deps),
                "cache_key": t.cache_key,
                "timeout_s": t.timeout_s,
                "allow_fail": t.allow_fail,
            }
            for t in dag.tasks.values()
        ]
        with open(cache_file, "wb") as f:
            f.write(
                json.dumps(cached_data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            )
    except Exception:
        pass

    return _compute_levels(dag)


def compute_levels(dag: DAG) -> List[List[str]]:
    """Public wrapper to compute leveled ordering for a DAG."""
    return _compute_levels(dag)
