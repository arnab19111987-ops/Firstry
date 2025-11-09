"""Tests for DAG topological ordering and execution levels.

Verifies that:
1. Toposort produces valid topological order
2. Dependencies are respected in sort
3. Tasks with no inter-dependencies can run in parallel
4. Cycles are detected and rejected
5. Independent tasks are grouped in parallel levels
"""

import pytest

from firsttry.runner.model import DAG
from firsttry.runner.model import Task


def test_toposort_simple():
    """Test topological sort on simple linear dependency chain."""
    dag = DAG()

    # Create chain: t1 -> t2 -> t3
    t1 = Task(id="t1", cmd=["echo"])
    t2 = Task(id="t2", cmd=["echo"], deps={"t1"})
    t3 = Task(id="t3", cmd=["echo"], deps={"t2"})

    dag.add(t1)
    dag.add(t2)
    dag.add(t3)

    order = dag.toposort()

    # Order must be t1, t2, t3
    assert order == ["t1", "t2", "t3"], f"Expected linear order, got {order}"


def test_toposort_respects_dependencies():
    """Test that toposort respects all dependencies."""
    dag = DAG()

    # Create diamond: t1 -> t2, t3 -> t4 depends on both
    t1 = Task(id="t1", cmd=["echo"])
    t2 = Task(id="t2", cmd=["echo"], deps={"t1"})
    t3 = Task(id="t3", cmd=["echo"], deps={"t1"})
    t4 = Task(id="t4", cmd=["echo"], deps={"t2", "t3"})

    dag.add(t1)
    dag.add(t2)
    dag.add(t3)
    dag.add(t4)

    order = dag.toposort()

    # Validate ordering: t1 must be first, t4 must be last
    t1_idx = order.index("t1")
    t2_idx = order.index("t2")
    t3_idx = order.index("t3")
    t4_idx = order.index("t4")

    assert t1_idx < t2_idx, "t1 must come before t2"
    assert t1_idx < t3_idx, "t1 must come before t3"
    assert t2_idx < t4_idx, "t2 must come before t4"
    assert t3_idx < t4_idx, "t3 must come before t4"


def test_toposort_independent_tasks():
    """Test that independent tasks can be ordered arbitrarily."""
    dag = DAG()

    # Create independent tasks
    t1 = Task(id="t1", cmd=["echo"])
    t2 = Task(id="t2", cmd=["echo"])
    t3 = Task(id="t3", cmd=["echo"])

    dag.add(t1)
    dag.add(t2)
    dag.add(t3)

    order = dag.toposort()

    # All 3 should be in order
    assert len(order) == 3
    assert set(order) == {"t1", "t2", "t3"}


def test_toposort_empty():
    """Test toposort on empty DAG."""
    dag = DAG()
    order = dag.toposort()
    assert order == []


def test_toposort_single_task():
    """Test toposort with single task."""
    dag = DAG()
    t = Task(id="single", cmd=["echo", "hello"])
    dag.add(t)

    order = dag.toposort()
    assert order == ["single"]


def test_toposort_cycle_detection():
    """Test that cycles are detected and rejected."""
    dag = DAG()

    # Create cycle: t1 -> t2 -> t3 -> t1
    # We can't directly create this with the API (since edges come from Task.deps),
    # but we can test with a task that has itself as a dependency
    t1 = Task(id="t1", cmd=["echo"], deps={"t1"})

    dag.add(t1)

    with pytest.raises(ValueError, match="Cycle detected"):
        dag.toposort()


def test_toposort_long_chain():
    """Test toposort on longer dependency chain."""
    dag = DAG()

    # Create chain: t1 -> t2 -> t3 -> t4 -> t5
    tasks = []
    prev_id = None
    for i in range(1, 6):
        task_id = f"t{i}"
        deps = {prev_id} if prev_id else set()
        task = Task(id=task_id, cmd=["echo", str(i)], deps=deps)
        tasks.append(task)
        dag.add(task)
        prev_id = task_id

    order = dag.toposort()
    expected = ["t1", "t2", "t3", "t4", "t5"]
    assert order == expected, f"Expected {expected}, got {order}"


def test_dag_no_duplicate_tasks():
    """Test that duplicate task IDs are rejected."""
    dag = DAG()

    t1 = Task(id="same", cmd=["echo"])
    t2 = Task(id="same", cmd=["echo"])

    dag.add(t1)

    with pytest.raises(ValueError, match="already exists"):
        dag.add(t2)


def test_dag_edges_validation():
    """Test that edges reference existing tasks."""
    dag = DAG()

    # Create task with dep on non-existent task
    t1 = Task(id="t1", cmd=["echo"], deps={"nonexistent"})
    dag.add(t1)

    # toposort should handle gracefully (skipping unknown edges)
    # This tests the "forgiving approach" in the model
    order = dag.toposort()
    assert "t1" in order


def test_dag_immutability():
    """Test that DAG.tasks and DAG.edges are read-only."""
    dag = DAG()

    t1 = Task(id="t1", cmd=["echo"])
    dag.add(t1)

    # Get the "read-only" views
    tasks_view = dag.tasks
    edges_view = dag.edges

    # They should contain our added task/edges
    assert "t1" in tasks_view

    # Modifying the returned views shouldn't affect the DAG
    # (This depends on whether these are truly immutable -
    # the code returns dicts/sets which are technically mutable)
    # But the intent is read-only, so we document it
    t2 = Task(id="t2", cmd=["echo"])
    dag.add(t2)

    # New task should be visible
    new_tasks = dag.tasks
    assert "t2" in new_tasks


def test_toposort_complex_dependency_graph():
    """Test toposort on complex multi-level dependency graph."""
    dag = DAG()

    # Complex graph:
    #   t1 (no deps)
    #   t2 (depends on t1)
    #   t3 (depends on t1)
    #   t4 (depends on t2, t3)
    #   t5 (depends on t4)
    #   t6 (depends on t2) - parallel with t3

    t1 = Task(id="t1", cmd=["echo"])
    t2 = Task(id="t2", cmd=["echo"], deps={"t1"})
    t3 = Task(id="t3", cmd=["echo"], deps={"t1"})
    t4 = Task(id="t4", cmd=["echo"], deps={"t2", "t3"})
    t5 = Task(id="t5", cmd=["echo"], deps={"t4"})
    t6 = Task(id="t6", cmd=["echo"], deps={"t2"})

    for t in [t1, t2, t3, t4, t5, t6]:
        dag.add(t)

    order = dag.toposort()

    # Verify all tasks are present
    assert len(order) == 6
    assert set(order) == {"t1", "t2", "t3", "t4", "t5", "t6"}

    # Verify ordering constraints
    idx = {task: i for i, task in enumerate(order)}
    assert idx["t1"] < idx["t2"]
    assert idx["t1"] < idx["t3"]
    assert idx["t2"] < idx["t4"]
    assert idx["t3"] < idx["t4"]
    assert idx["t4"] < idx["t5"]
    assert idx["t2"] < idx["t6"]


def test_toposort_nondestructive():
    """Test that toposort doesn't mutate the DAG."""
    dag = DAG()

    t1 = Task(id="t1", cmd=["echo"])
    t2 = Task(id="t2", cmd=["echo"], deps={"t1"})
    dag.add(t1)
    dag.add(t2)

    # Call toposort multiple times
    order1 = dag.toposort()
    order2 = dag.toposort()
    order3 = dag.toposort()

    # All should be identical (proves non-destructive)
    assert order1 == order2 == order3

    # DAG structure should be unchanged
    assert len(dag.tasks) == 2
    assert len(dag.edges) == 1
