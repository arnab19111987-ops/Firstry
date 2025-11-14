"""Tests for DAG orchestration: planner, executor, and config loading."""

import tempfile
from pathlib import Path

import pytest

from firsttry.runner.config import ConfigLoader
from firsttry.runner.executor import Executor
from firsttry.runner.model import DAG
from firsttry.runner.model import Task
from firsttry.runner.planner import Planner


class TestTaskModel:
    """Test Task sealed envelope (frozen dataclass)."""

    def test_task_creation(self) -> None:
        """Test basic task creation."""
        task = Task(
            id="test_task",
            cmd=["echo", "hello"],
            deps={"dep1", "dep2"},
        )
        assert task.id == "test_task"
        assert task.cmd == ["echo", "hello"]
        assert task.deps == {"dep1", "dep2"}

    def test_task_immutable(self) -> None:
        """Test that task is frozen (immutable)."""
        task = Task(id="test", cmd=["echo"])
        with pytest.raises(Exception):
            task.id = "modified"  # type: ignore

    def test_task_defaults(self) -> None:
        """Test task default values."""
        task = Task(id="test", cmd=["ls"])
        assert task.deps == set()
        assert task.resources == set()
        assert task.timeout_s == 0
        assert task.allow_fail is False
        assert task.cache_key == ""


class TestDAGModel:
    """Test DAG with non-destructive toposort."""

    def test_add_task(self) -> None:
        """Test adding tasks to DAG."""
        dag = DAG()
        t1 = Task(id="t1", cmd=["echo"])
        t2 = Task(id="t2", cmd=["echo"], deps={"t1"})
        dag.add(t1)
        dag.add(t2)
        assert len(dag.tasks) == 2
        assert len(dag.edges) == 1

    def test_duplicate_task_raises(self) -> None:
        """Test that adding duplicate task ID raises."""
        dag = DAG()
        t1 = Task(id="t1", cmd=["echo"])
        dag.add(t1)
        with pytest.raises(ValueError, match="already exists"):
            dag.add(t1)

    def test_toposort_simple(self) -> None:
        """Test topological sort on simple DAG."""
        dag = DAG()
        t1 = Task(id="t1", cmd=["echo"])
        t2 = Task(id="t2", cmd=["echo"], deps={"t1"})
        t3 = Task(id="t3", cmd=["echo"], deps={"t2"})
        dag.add(t1)
        dag.add(t2)
        dag.add(t3)
        order = dag.toposort()
        assert order == ["t1", "t2", "t3"]

    def test_toposort_nondestructive(self) -> None:
        """Test that toposort doesn't mutate DAG."""
        dag = DAG()
        t1 = Task(id="t1", cmd=["echo"])
        t2 = Task(id="t2", cmd=["echo"], deps={"t1"})
        dag.add(t1)
        dag.add(t2)

        # Multiple toposorts should work identically
        order1 = dag.toposort()
        order2 = dag.toposort()
        assert order1 == order2

        # Original graph unchanged
        assert len(dag.tasks) == 2
        assert len(dag.edges) == 1

    def test_toposort_multiple_valid_orders(self) -> None:
        """Test DAG with multiple valid topological orders."""
        dag = DAG()
        # Graph: t1 -> t3, t2 -> t3
        # Valid orders: [t1, t2, t3] or [t2, t1, t3]
        t1 = Task(id="t1", cmd=["echo"])
        t2 = Task(id="t2", cmd=["echo"])
        t3 = Task(id="t3", cmd=["echo"], deps={"t1", "t2"})
        dag.add(t1)
        dag.add(t2)
        dag.add(t3)
        order = dag.toposort()

        # Both t1 and t2 must come before t3
        assert order.index("t3") > order.index("t1")
        assert order.index("t3") > order.index("t2")

    def test_toposort_cycle_detection(self) -> None:
        """Test cycle detection in toposort."""
        dag = DAG()
        # Create a cycle: t1 -> t2 -> t1
        t1 = Task(id="t1", cmd=["echo"], deps={"t2"})
        t2 = Task(id="t2", cmd=["echo"], deps={"t1"})
        dag.add(t1)
        dag.add(t2)

        with pytest.raises(ValueError, match="Cycle detected"):
            dag.toposort()

    def test_as_runner_inputs(self) -> None:
        """Test as_runner_inputs export."""
        dag = DAG()
        t1 = Task(id="t1", cmd=["echo"])
        t2 = Task(id="t2", cmd=["echo"], deps={"t1"})
        dag.add(t1)
        dag.add(t2)

        tasks, edges = dag.as_runner_inputs()
        assert len(tasks) == 2
        assert len(edges) == 1
        assert ("t1", "t2") in edges


class TestPlanner:
    """Test DAG planner."""

    def test_build_dag_default(self) -> None:
        """Test building DAG with defaults."""
        planner = Planner()
        root = Path("/tmp")
        dag = planner.build_dag({}, root)

        # Default chain: ruff -> mypy -> pytest
        order = dag.toposort()
        assert order == ["ruff", "mypy", "pytest"]

    def test_build_dag_custom_commands(self) -> None:
        """Test building DAG with custom commands."""
        planner = Planner()
        config = {
            "ruff_cmd": ["ruff", "check", "--select", "E"],
            "mypy_cmd": ["mypy", "src", "--strict"],
            "pytest_cmd": ["pytest", "tests", "-v"],
        }
        dag = planner.build_dag(config, Path("/tmp"))

        ruff_task = dag.tasks["ruff"]
        assert ruff_task.cmd == ["ruff", "check", "--select", "E"]

        mypy_task = dag.tasks["mypy"]
        assert mypy_task.cmd == ["mypy", "src", "--strict"]

    def test_build_dag_custom_dependencies(self) -> None:
        """Test building DAG with custom dependencies."""
        planner = Planner()
        config = {
            "ruff_depends_on": {"lint_prep"},
            "mypy_depends_on": {"ruff", "type_prep"},
            "pytest_depends_on": {"mypy"},
        }
        dag = planner.build_dag(config, Path("/tmp"))

        # Note: custom deps reference unknown tasks, which are skipped
        # so the default chain should still be preserved
        ruff_task = dag.tasks["ruff"]
        assert ruff_task.deps == {"lint_prep"}

    def test_build_dag_cache_keys(self) -> None:
        """Test that tasks have cache keys."""
        planner = Planner()
        dag = planner.build_dag({}, Path("/tmp"))

        for task_id in ["ruff", "mypy", "pytest"]:
            task = dag.tasks[task_id]
            assert task.cache_key
            assert len(task.cache_key) == 16  # SHA256 first 16 chars


class TestExecutor:
    """Test task executor."""

    def test_executor_simple(self) -> None:
        """Test executor with simple tasks."""
        dag = DAG()
        # Create a task that succeeds
        t1 = Task(id="test_success", cmd=["true"])
        dag.add(t1)

        executor = Executor(dag, use_rust=False)
        results = executor.execute()

        assert results["test_success"] == 0

    def test_executor_failure(self) -> None:
        """Test executor with failing task."""
        dag = DAG()
        t1 = Task(id="test_fail", cmd=["false"])
        dag.add(t1)

        executor = Executor(dag, use_rust=False)
        results = executor.execute()

        assert results["test_fail"] != 0

    def test_executor_failure_allowed(self) -> None:
        """Test executor with allowed failure."""
        dag = DAG()
        t1 = Task(id="fail_allowed", cmd=["false"], allow_fail=True)
        t2 = Task(id="after_fail", cmd=["true"], deps={"fail_allowed"})
        dag.add(t1)
        dag.add(t2)

        executor = Executor(dag, use_rust=False)
        results = executor.execute()

        # Second task should still execute despite first failing
        assert "after_fail" in results

    def test_executor_dependency_order(self) -> None:
        """Test executor respects dependency order."""
        dag = DAG()

        # Create a temp file to track execution order
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
            marker_file = f.name

        try:
            t1 = Task(id="t1", cmd=["sh", "-c", f"echo 1 >> {marker_file}"])
            t2 = Task(id="t2", cmd=["sh", "-c", f"echo 2 >> {marker_file}"], deps={"t1"})
            dag.add(t1)
            dag.add(t2)

            executor = Executor(dag, use_rust=False)
            results = executor.execute()

            # Verify both executed
            assert results["t1"] == 0
            assert results["t2"] == 0

            # Verify order by checking file contents
            with open(marker_file) as f:
                lines = f.read().strip().split("\n")
                assert lines == ["1", "2"]
        finally:
            Path(marker_file).unlink()

    def test_executor_timeout(self) -> None:
        """Test executor timeout handling."""
        dag = DAG()
        # Task that sleeps longer than timeout
        t1 = Task(id="timeout_task", cmd=["sleep", "10"], timeout_s=1)
        dag.add(t1)

        executor = Executor(dag, use_rust=False)
        results = executor.execute()

        # Should have timeout exit code (124)
        assert results["timeout_task"] == 124


class TestConfigLoader:
    """Test configuration loader."""

    def test_load_toml(self) -> None:
        """Test loading TOML configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[workflow]\nruff_cmd = ["ruff", "check"]\n')
            config_path = f.name

        try:
            config = ConfigLoader.load(config_path)
            assert "workflow" in config
            assert config["workflow"]["ruff_cmd"] == ["ruff", "check"]
        finally:
            Path(config_path).unlink()

    def test_load_nonexistent_file(self) -> None:
        """Test loading from nonexistent file."""
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load("/nonexistent/path/config.toml")

    def test_load_workflow(self) -> None:
        """Test loading workflow section."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[workflow]\nruff_cmd = ["ruff"]\n[resources]\nmemory_gb = 4\n')
            config_path = f.name

        try:
            workflow = ConfigLoader.load_workflow(config_path)
            assert workflow["ruff_cmd"] == ["ruff"]
        finally:
            Path(config_path).unlink()

    def test_load_resources(self) -> None:
        """Test loading resources section."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("[resources]\nmemory_gb = 4\ntimeout_s = 300\n")
            config_path = f.name

        try:
            resources = ConfigLoader.load_resources(config_path)
            assert resources["memory_gb"] == 4
            assert resources["timeout_s"] == 300
        finally:
            Path(config_path).unlink()
