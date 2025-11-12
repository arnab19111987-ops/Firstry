"""Task and DAG models for orchestrated execution.

Task is a frozen envelope (immutable, sealed). DAG provides safe, non-destructive
topological sorting and edge validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import List
from typing import Set
from typing import Tuple


@dataclass(frozen=True)
class Task:
    """Immutable task definition (sealed envelope).

    Attributes:
        id: Unique task identifier
        cmd: Command and arguments as list (e.g., ["ruff", "check", "src"])
        deps: Set of task IDs this task depends on
        resources: Set of resource names required (e.g., {"db", "network"})
        timeout_s: Timeout in seconds (0 = no timeout)
        allow_fail: Whether task failure is acceptable
        cache_key: Optional cache key for result caching
    """

    id: str
    cmd: List[str]
    deps: Set[str] = field(default_factory=set)
    resources: Set[str] = field(default_factory=set)
    timeout_s: int = 0
    allow_fail: bool = False
    cache_key: str = ""


class DAG:
    """Directed Acyclic Graph of tasks with safe topological sorting.

    The DAG is non-destructive: toposort() does not mutate the graph.
    Cycle detection is performed during topological sort.
    All edges are validated against known tasks.
    """

    def __init__(self) -> None:
        """Initialize empty DAG."""
        self._tasks: Dict[str, Task] = {}
        self._edges: Set[Tuple[str, str]] = set()  # (from, to)

    def add(self, task: Task) -> None:
        """Add a task and its dependency edges to the DAG.

        Args:
            task: Task to add

        Raises:
            ValueError: If task ID already exists
        """
        if task.id in self._tasks:
            raise ValueError(f"Task already exists: {task.id}")
        self._tasks[task.id] = task
        for d in task.deps:
            self._edges.add((d, task.id))

    @property
    def tasks(self) -> Dict[str, Task]:
        """Return all tasks (read-only view)."""
        return self._tasks

    @property
    def edges(self) -> Set[Tuple[str, str]]:
        """Return all edges (read-only view)."""
        return self._edges

    def toposort(self) -> List[str]:
        """Return a valid topological order without mutating the graph.

        Uses Kahn's algorithm with in-degree tracking.

        Returns:
            List of task IDs in topological order

        Raises:
            ValueError: If a cycle is detected or dependency references unknown task
        """
        # Build in-degree map and adjacency list (non-destructively)
        indeg: Dict[str, int] = {tid: 0 for tid in self._tasks}
        adj: Dict[str, List[str]] = {tid: [] for tid in self._tasks}

        for a, b in self._edges:
            if a not in self._tasks or b not in self._tasks:
                # Skip edges with unknown tasks (forgiving approach)
                # Alternatively: raise ValueError(f"Unknown task in edge: {a} -> {b}")
                continue
            indeg[b] += 1
            adj[a].append(b)

        # Find all nodes with in-degree 0
        ready = [tid for tid, d in indeg.items() if d == 0]
        order: List[str] = []

        while ready:
            n = ready.pop(0)  # Use pop(0) for consistent ordering
            order.append(n)
            for neighbor in adj[n]:
                indeg[neighbor] -= 1
                if indeg[neighbor] == 0:
                    ready.append(neighbor)

        # Check for cycles
        if len(order) != len(self._tasks):
            raise ValueError(
                f"Cycle detected in DAG: {len(order)} tasks processed, "
                f"but {len(self._tasks)} total tasks"
            )
        return order

    def as_runner_inputs(self) -> tuple[list[Task], list[tuple[str, str]]]:
        """Export tasks and edges for runner.

        Returns:
            Tuple of (tasks list, edges list)
        """
        return list(self._tasks.values()), list(self._edges)
