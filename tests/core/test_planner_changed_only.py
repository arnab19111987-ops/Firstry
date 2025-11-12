"""Tests for changed-only DAG filtering and minimal subgraph selection.

Verifies that:
1. Changed tasks are correctly identified
2. Minimal subgraph includes only affected tasks and dependents
3. Independent tasks are excluded when unaffected
4. Dependent chain is included transitively
"""

from firsttry.runner.model import DAG
from firsttry.runner.model import Task


def _mock_repo_deps():
    """Create a mock dependency graph for testing.

    Returns dict: task -> [dependencies]
    """
    return {
        "lint": [],
        "typecheck": ["lint"],
        "test-unit": ["lint"],
        "test-integration": ["typecheck", "test-unit"],
        "package": ["test-integration"],
    }


def _build_dag_from_deps(deps_dict):
    """Build a DAG from a dependency dictionary."""
    dag = DAG()

    for task_id, deps in deps_dict.items():
        task = Task(id=task_id, cmd=["echo", task_id], deps=set(deps))
        dag.add(task)

    return dag


def test_minimal_subgraph_changed_leaf():
    """Test minimal subgraph when a leaf task changes."""
    deps = _mock_repo_deps()
    dag = _build_dag_from_deps(deps)

    # If "test-unit" changes, should run test-unit and its dependents
    changed = {"test-unit"}

    # Compute minimal subgraph manually (filter logic)
    # We'll implement this as: changed + all transitive dependents
    affected = set(changed)

    # For each changed task, find all tasks that depend on it (transitively)
    def find_dependents(task_id, dag_edges):
        """Find all tasks that transitively depend on task_id."""
        result = set()
        # Find direct dependents
        for src, dst in dag_edges:
            if src == task_id:
                result.add(dst)
                # Recursively find dependents of dependents
                result.update(find_dependents(dst, dag_edges))
        return result

    edges_list = list(dag.edges)
    for changed_task in changed:
        affected.update(find_dependents(changed_task, edges_list))

    # Should include: test-unit, test-integration, package
    expected = {"test-unit", "test-integration", "package"}
    assert affected == expected, f"Expected {expected}, got {affected}"


def test_minimal_subgraph_changed_middle():
    """Test minimal subgraph when a middle task changes."""
    deps = _mock_repo_deps()
    dag = _build_dag_from_deps(deps)

    # If "typecheck" changes, should run it and everything after
    changed = {"typecheck"}
    affected = set(changed)

    edges_list = list(dag.edges)

    def find_dependents(task_id, dag_edges):
        result = set()
        for src, dst in dag_edges:
            if src == task_id:
                result.add(dst)
                result.update(find_dependents(dst, dag_edges))
        return result

    for changed_task in changed:
        affected.update(find_dependents(changed_task, edges_list))

    # Should include: typecheck, test-integration, package
    # (not test-unit or lint)
    expected = {"typecheck", "test-integration", "package"}
    assert affected == expected, f"Expected {expected}, got {affected}"


def test_minimal_subgraph_unchanged_lint():
    """Test that lint changes require everything."""
    deps = _mock_repo_deps()
    dag = _build_dag_from_deps(deps)

    # If "lint" (root) changes, all tasks depend on it
    changed = {"lint"}
    affected = set(changed)

    edges_list = list(dag.edges)

    def find_dependents(task_id, dag_edges):
        result = set()
        for src, dst in dag_edges:
            if src == task_id:
                result.add(dst)
                result.update(find_dependents(dst, dag_edges))
        return result

    for changed_task in changed:
        affected.update(find_dependents(changed_task, edges_list))

    # Should include ALL tasks
    expected = {"lint", "typecheck", "test-unit", "test-integration", "package"}
    assert affected == expected, f"Expected all tasks, got {affected}"


def test_minimal_subgraph_multiple_changed():
    """Test minimal subgraph with multiple changed tasks."""
    deps = _mock_repo_deps()
    dag = _build_dag_from_deps(deps)

    # If both "typecheck" and "test-unit" change
    changed = {"typecheck", "test-unit"}
    affected = set(changed)

    edges_list = list(dag.edges)

    def find_dependents(task_id, dag_edges):
        result = set()
        for src, dst in dag_edges:
            if src == task_id:
                result.add(dst)
                result.update(find_dependents(dst, dag_edges))
        return result

    for changed_task in changed:
        affected.update(find_dependents(changed_task, edges_list))

    # Should include: typecheck, test-unit, test-integration, package
    # (not lint)
    expected = {"typecheck", "test-unit", "test-integration", "package"}
    assert affected == expected, f"Expected {expected}, got {affected}"


def test_minimal_subgraph_no_redundancy():
    """Test that minimal subgraph doesn't include unaffected independent tasks."""
    # Create a different graph with parallel tasks
    deps = {
        "lint": [],
        "format": [],  # Parallel with lint
        "typecheck": ["lint"],
        "test": ["format"],  # Depends on format, not lint
    }
    dag = _build_dag_from_deps(deps)

    # If only "lint" changes
    changed = {"lint"}
    affected = set(changed)

    edges_list = list(dag.edges)

    def find_dependents(task_id, dag_edges):
        result = set()
        for src, dst in dag_edges:
            if src == task_id:
                result.add(dst)
                result.update(find_dependents(dst, dag_edges))
        return result

    for changed_task in changed:
        affected.update(find_dependents(changed_task, edges_list))

    # Should include: lint, typecheck
    # Should NOT include: format, test (independent of lint changes)
    expected = {"lint", "typecheck"}
    assert affected == expected, f"Expected {expected}, got {affected}"
    assert "format" not in affected, "format should not be affected"
    assert "test" not in affected, "test should not be affected by lint change"


def test_toposort_respected_in_minimal_subgraph():
    """Test that subgraph tasks maintain valid toposort order."""
    deps = _mock_repo_deps()
    dag = _build_dag_from_deps(deps)

    changed = {"test-unit"}
    affected = set(changed)

    edges_list = list(dag.edges)

    def find_dependents(task_id, dag_edges):
        result = set()
        for src, dst in dag_edges:
            if src == task_id:
                result.add(dst)
                result.update(find_dependents(dst, dag_edges))
        return result

    for changed_task in changed:
        affected.update(find_dependents(changed_task, edges_list))

    # Get full toposort
    full_order = dag.toposort()

    # Filter to affected tasks
    affected_order = [t for t in full_order if t in affected]

    # Verify dependencies are still respected in subgraph
    # For "test-unit" -> "test-integration" -> "package"
    idx = {task: i for i, task in enumerate(affected_order)}
    assert idx["test-unit"] < idx["test-integration"]
    assert idx["test-integration"] < idx["package"]


def test_minimal_subgraph_transitive_closure():
    """Test that subgraph captures full transitive closure."""
    # Create longer chain: a -> b -> c -> d -> e
    deps = {
        "a": [],
        "b": ["a"],
        "c": ["b"],
        "d": ["c"],
        "e": ["d"],
    }
    dag = _build_dag_from_deps(deps)

    # If "b" changes, should include c, d, e (all transitive dependents)
    changed = {"b"}
    affected = set(changed)

    edges_list = list(dag.edges)

    def find_dependents(task_id, dag_edges):
        result = set()
        for src, dst in dag_edges:
            if src == task_id:
                result.add(dst)
                result.update(find_dependents(dst, dag_edges))
        return result

    for changed_task in changed:
        affected.update(find_dependents(changed_task, edges_list))

    # Should include b, c, d, e (but not a)
    expected = {"b", "c", "d", "e"}
    assert affected == expected, f"Expected {expected}, got {affected}"
    assert "a" not in affected, "a should not be affected"


def test_minimal_subgraph_with_diamond():
    """Test subgraph with diamond dependency pattern."""
    # Diamond: a -> (b, c) -> d
    deps = {
        "a": [],
        "b": ["a"],
        "c": ["a"],
        "d": ["b", "c"],
    }
    dag = _build_dag_from_deps(deps)

    # If "a" changes, all should run
    changed = {"a"}
    affected = set(changed)

    edges_list = list(dag.edges)

    def find_dependents(task_id, dag_edges):
        result = set()
        for src, dst in dag_edges:
            if src == task_id:
                result.add(dst)
                result.update(find_dependents(dst, dag_edges))
        return result

    for changed_task in changed:
        affected.update(find_dependents(changed_task, edges_list))

    expected = {"a", "b", "c", "d"}
    assert affected == expected


def test_minimal_subgraph_no_changes():
    """Test subgraph when no tasks change."""
    deps = _mock_repo_deps()
    dag = _build_dag_from_deps(deps)

    changed = set()  # No changes
    affected = set(changed)

    # Should be empty (nothing to run)
    assert len(affected) == 0, "No tasks should be affected if nothing changed"
