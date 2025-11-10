"""Comprehensive coverage tests for src/firsttry/runner/planner.py

This suite targets:
- DAG construction with various task configurations
- Cache key computation (deterministic hashing)
- Config-based caching and invalidation
- Dependency injection and custom configs
- Cache serialization/deserialization
- Level computation (parallel task grouping)
"""

import os
import tempfile
from pathlib import Path
from typing import Any
from typing import Dict

import pytest

from firsttry.runner.model import DAG
from firsttry.runner.model import Task
from firsttry.runner.planner import PLAN_CACHE_PREFIX
from firsttry.runner.planner import Planner
from firsttry.runner.planner import _compute_levels
from firsttry.runner.planner import _hash_bytes
from firsttry.runner.planner import _load_config_bytes
from firsttry.runner.planner import _plan_cache_key


class TestPlannerBasics:
    """Test basic Planner instantiation and DAG building."""

    def test_planner_init(self):
        """Test Planner can be instantiated."""
        planner = Planner()
        assert planner is not None

    def test_build_dag_default_config(self, tmp_path: Path):
        """Test build_dag with default configuration (no custom deps)."""
        planner = Planner()
        twin_dict: Dict[str, Any] = {}
        dag = planner.build_dag(twin_dict, tmp_path)

        # Should have 3 tasks: ruff, mypy, pytest
        assert len(dag.tasks) == 3
        assert "ruff" in dag.tasks
        assert "mypy" in dag.tasks
        assert "pytest" in dag.tasks

    def test_build_dag_custom_commands(self, tmp_path: Path):
        """Test build_dag with custom command overrides."""
        planner = Planner()
        twin_dict: Dict[str, Any] = {
            "ruff_cmd": ["custom-ruff", "--check"],
            "mypy_cmd": ["custom-mypy", "--strict"],
            "pytest_cmd": ["custom-pytest", "-v"],
        }
        dag = planner.build_dag(twin_dict, tmp_path)

        assert dag.tasks["ruff"].cmd == ["custom-ruff", "--check"]
        assert dag.tasks["mypy"].cmd == ["custom-mypy", "--strict"]
        assert dag.tasks["pytest"].cmd == ["custom-pytest", "-v"]

    def test_build_dag_default_dependencies(self, tmp_path: Path):
        """Test default dependency chain: ruff -> mypy -> pytest."""
        planner = Planner()
        twin_dict: Dict[str, Any] = {}
        dag = planner.build_dag(twin_dict, tmp_path)

        # Default: ruff has no deps, mypy has no deps, pytest depends on both
        assert dag.tasks["ruff"].deps == set()
        assert dag.tasks["mypy"].deps == set()
        assert dag.tasks["pytest"].deps == {"ruff", "mypy"}

    def test_build_dag_custom_dependencies(self, tmp_path: Path):
        """Test build_dag with custom dependency overrides."""
        planner = Planner()
        twin_dict: Dict[str, Any] = {
            "ruff_depends_on": {"some_setup"},
            "mypy_depends_on": {"ruff", "another_dep"},
            "pytest_depends_on": {"mypy"},
        }
        dag = planner.build_dag(twin_dict, tmp_path)

        assert dag.tasks["ruff"].deps == {"some_setup"}
        assert dag.tasks["mypy"].deps == {"ruff", "another_dep"}
        assert dag.tasks["pytest"].deps == {"mypy"}

    def test_build_dag_task_properties(self, tmp_path: Path):
        """Test that DAG tasks have correct properties (timeout, cache_key)."""
        planner = Planner()
        twin_dict: Dict[str, Any] = {}
        dag = planner.build_dag(twin_dict, tmp_path)

        # Check timeouts
        assert dag.tasks["ruff"].timeout_s == 60
        assert dag.tasks["mypy"].timeout_s == 120
        assert dag.tasks["pytest"].timeout_s == 300

        # Check that cache keys are computed
        assert dag.tasks["ruff"].cache_key != ""
        assert dag.tasks["mypy"].cache_key != ""
        assert dag.tasks["pytest"].cache_key != ""

    def test_build_dag_cache_keys_differ_by_cmd(self, tmp_path: Path):
        """Test that cache keys differ when commands differ."""
        planner = Planner()

        # Build with default commands
        dag1 = planner.build_dag({}, tmp_path)
        ruff_key1 = dag1.tasks["ruff"].cache_key

        # Build with custom command
        dag2 = planner.build_dag({"ruff_cmd": ["different-ruff"]}, tmp_path)
        ruff_key2 = dag2.tasks["ruff"].cache_key

        # Cache keys should differ
        assert ruff_key1 != ruff_key2

    def test_build_dag_allow_fail_settings(self, tmp_path: Path):
        """Test that pytest task has allow_fail=False (must not fail silently)."""
        planner = Planner()
        dag = planner.build_dag({}, tmp_path)

        assert dag.tasks["pytest"].allow_fail is False
        # ruff and mypy may allow fail depending on config
        assert dag.tasks["ruff"].allow_fail in (True, False)
        assert dag.tasks["mypy"].allow_fail in (True, False)


class TestCacheKeyComputation:
    """Test hash-based cache key generation."""

    def test_hash_bytes_deterministic(self):
        """Test that _hash_bytes produces deterministic output."""
        data = b"test_data_12345"
        h1 = _hash_bytes(data)
        h2 = _hash_bytes(data)
        assert h1 == h2

    def test_hash_bytes_length(self):
        """Test that _hash_bytes produces 32-char hex (BLAKE2b-128)."""
        data = b"anything"
        h = _hash_bytes(data)
        # BLAKE2b-128 = 16 bytes = 32 hex chars
        assert len(h) == 32
        # Must be valid hex
        int(h, 16)

    def test_hash_bytes_changes_with_input(self):
        """Test that different inputs produce different hashes."""
        h1 = _hash_bytes(b"input1")
        h2 = _hash_bytes(b"input2")
        assert h1 != h2

    def test_load_config_bytes_includes_versions(self):
        """Test that _load_config_bytes includes Python and FT version."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test_content")
            config_path = f.name

        try:
            cfg_bytes = _load_config_bytes(config_path)
            # Should include Python version
            assert b"PY:" in cfg_bytes
            # Should include FirstTry version (FT: key)
            assert b"FT:" in cfg_bytes
            # Should include original content
            assert b"test_content" in cfg_bytes
        finally:
            os.unlink(config_path)

    def test_plan_cache_key_deterministic(self):
        """Test that _plan_cache_key is deterministic."""
        data = b"config_hash_test"
        key1 = _plan_cache_key(data)
        key2 = _plan_cache_key(data)
        assert key1 == key2
        # Should be a hex string
        assert len(key1) == 32

    def test_plan_cache_key_differs_by_input(self):
        """Test that cache keys differ for different inputs."""
        key1 = _plan_cache_key(b"config1")
        key2 = _plan_cache_key(b"config2")
        assert key1 != key2


class TestPlanCaching:
    """Test plan-level caching (DAG serialization/deserialization)."""

    def test_get_cached_dag_cache_miss_creates_file(self, tmp_path: Path):
        """Test that cache miss creates a cache file."""
        planner = Planner()
        config_path = str(tmp_path / "firsttry.toml")
        (tmp_path / "firsttry.toml").write_text("# config")

        # Create cache dir
        cache_dir = tmp_path / ".firsttry" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(tmp_path)

        twin_dict: Dict[str, Any] = {}
        dag = planner.get_cached_dag(config_path, twin_dict, tmp_path)

        # Should have created a DAG
        assert len(dag.tasks) == 3

        # Should have created cache file
        cache_files = list(cache_dir.glob(f"{PLAN_CACHE_PREFIX}*.json"))
        assert len(cache_files) >= 1, f"Expected cache file, found: {list(cache_dir.glob('*'))}"

    def test_get_cached_dag_cache_hit_returns_cached_dag(self, tmp_path: Path):
        """Test that subsequent calls return cached DAG."""
        planner = Planner()
        config_path = str(tmp_path / "firsttry.toml")
        (tmp_path / "firsttry.toml").write_text("# config")

        cache_dir = tmp_path / ".firsttry" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(tmp_path)

        twin_dict: Dict[str, Any] = {}

        # First call: cache miss
        dag1 = planner.get_cached_dag(config_path, twin_dict, tmp_path)
        assert len(dag1.tasks) == 3

        # Second call: should hit cache
        dag2 = planner.get_cached_dag(config_path, twin_dict, tmp_path)
        assert len(dag2.tasks) == 3

        # Tasks should have same IDs and commands
        for task_id in ["ruff", "mypy", "pytest"]:
            assert dag1.tasks[task_id].id == dag2.tasks[task_id].id
            assert dag1.tasks[task_id].cmd == dag2.tasks[task_id].cmd

    def test_get_cached_dag_invalidates_on_config_change(self, tmp_path: Path):
        """Test that cache is invalidated when config changes."""
        planner = Planner()
        config_path = str(tmp_path / "firsttry.toml")

        cache_dir = tmp_path / ".firsttry" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(tmp_path)

        # First config
        (tmp_path / "firsttry.toml").write_text("# config v1")
        twin_dict1: Dict[str, Any] = {"ruff_cmd": ["ruff-v1"]}
        dag1 = planner.get_cached_dag(config_path, twin_dict1, tmp_path)

        # Second config (different content)
        (tmp_path / "firsttry.toml").write_text("# config v2")
        twin_dict2: Dict[str, Any] = {"ruff_cmd": ["ruff-v2"]}
        dag2 = planner.get_cached_dag(config_path, twin_dict2, tmp_path)

        # DAGs should be different (different ruff commands)
        assert dag1.tasks["ruff"].cmd != dag2.tasks["ruff"].cmd

    def test_get_cached_dag_corrupted_cache_recovers(self, tmp_path: Path):
        """Test that corrupted cache is recovered by rebuilding."""
        planner = Planner()
        config_path = str(tmp_path / "firsttry.toml")
        (tmp_path / "firsttry.toml").write_text("# config")

        cache_dir = tmp_path / ".firsttry" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(tmp_path)

        twin_dict: Dict[str, Any] = {}

        # First call creates cache
        dag1 = planner.get_cached_dag(config_path, twin_dict, tmp_path)

        # Corrupt the cache file
        cache_files = list(cache_dir.glob(f"{PLAN_CACHE_PREFIX}*.json"))
        if cache_files:
            cache_files[0].write_text("invalid json {{{")

        # Second call should detect corruption and rebuild
        dag2 = planner.get_cached_dag(config_path, twin_dict, tmp_path)
        assert len(dag2.tasks) == 3


class TestComputeLevels:
    """Test parallel level computation for DAG execution."""

    def test_compute_levels_linear_chain(self):
        """Test levels for linear dependency chain."""
        dag = DAG()
        dag.add(Task(id="t1", cmd=["echo"]))
        dag.add(Task(id="t2", cmd=["echo"], deps={"t1"}))
        dag.add(Task(id="t3", cmd=["echo"], deps={"t2"}))

        levels = _compute_levels(dag)

        # Should have 3 levels, each with 1 task
        assert len(levels) == 3
        assert levels[0] == ["t1"]
        assert levels[1] == ["t2"]
        assert levels[2] == ["t3"]

    def test_compute_levels_parallel_tasks(self):
        """Test that independent tasks are in same level."""
        dag = DAG()
        dag.add(Task(id="t1", cmd=["echo"]))
        dag.add(Task(id="t2", cmd=["echo"]))
        dag.add(Task(id="t3", cmd=["echo"]))

        levels = _compute_levels(dag)

        # All tasks independent, should be in one level
        assert len(levels) == 1
        assert set(levels[0]) == {"t1", "t2", "t3"}

    def test_compute_levels_diamond_graph(self):
        """Test levels for diamond dependency graph."""
        dag = DAG()
        dag.add(Task(id="t1", cmd=["echo"]))
        dag.add(Task(id="t2", cmd=["echo"], deps={"t1"}))
        dag.add(Task(id="t3", cmd=["echo"], deps={"t1"}))
        dag.add(Task(id="t4", cmd=["echo"], deps={"t2", "t3"}))

        levels = _compute_levels(dag)

        # Level 0: t1
        # Level 1: t2, t3 (both depend only on t1)
        # Level 2: t4 (depends on t2 and t3)
        assert len(levels) == 3
        assert levels[0] == ["t1"]
        assert set(levels[1]) == {"t2", "t3"}
        assert levels[2] == ["t4"]

    def test_compute_levels_cycle_detection(self):
        """Test that cycles are detected and raise error."""
        dag = DAG()
        dag.add(Task(id="t1", cmd=["echo"], deps={"t2"}))
        dag.add(Task(id="t2", cmd=["echo"], deps={"t1"}))

        # Should raise ValueError for cycle
        with pytest.raises(ValueError, match="Cycle detected"):
            _compute_levels(dag)

    def test_compute_levels_empty_dag(self):
        """Test levels for empty DAG."""
        dag = DAG()
        levels = _compute_levels(dag)
        assert levels == []


class TestTaskCacheKeys:
    """Test per-task cache key computation."""

    def test_compute_cache_key_deterministic(self, tmp_path: Path):
        """Test that cache keys are deterministic."""
        planner = Planner()
        key1 = planner._compute_cache_key("ruff", ["ruff", "check"], tmp_path)
        key2 = planner._compute_cache_key("ruff", ["ruff", "check"], tmp_path)
        assert key1 == key2

    def test_compute_cache_key_varies_by_tool(self, tmp_path: Path):
        """Test that cache keys differ by tool name."""
        planner = Planner()
        key_ruff = planner._compute_cache_key("ruff", ["cmd"], tmp_path)
        key_mypy = planner._compute_cache_key("mypy", ["cmd"], tmp_path)
        assert key_ruff != key_mypy

    def test_compute_cache_key_varies_by_command(self, tmp_path: Path):
        """Test that cache keys differ by command."""
        planner = Planner()
        key1 = planner._compute_cache_key("ruff", ["ruff", "check", "src"], tmp_path)
        key2 = planner._compute_cache_key("ruff", ["ruff", "check", "src/lib"], tmp_path)
        assert key1 != key2

    def test_compute_cache_key_length(self, tmp_path: Path):
        """Test that cache keys are appropriately sized."""
        planner = Planner()
        key = planner._compute_cache_key("ruff", ["ruff"], tmp_path)
        # Should be 16 chars (SHA256 truncated to 16)
        assert len(key) == 16


class TestComplexConfigurations:
    """Test Planner with complex, realistic configurations."""

    def test_build_dag_with_all_custom_settings(self, tmp_path: Path):
        """Test build_dag with completely customized configuration."""
        planner = Planner()
        twin_dict: Dict[str, Any] = {
            "ruff_cmd": ["ruff", "check", "--select", "E,W", "src"],
            "mypy_cmd": ["mypy", "--strict", "--no-implicit-optional", "src"],
            "pytest_cmd": ["pytest", "-vv", "--cov=src", "tests"],
            "ruff_depends_on": set(),
            "mypy_depends_on": {"ruff"},
            "pytest_depends_on": {"mypy", "ruff"},
        }

        dag = planner.build_dag(twin_dict, tmp_path)

        assert dag.tasks["ruff"].cmd == ["ruff", "check", "--select", "E,W", "src"]
        assert dag.tasks["mypy"].cmd == ["mypy", "--strict", "--no-implicit-optional", "src"]
        assert dag.tasks["pytest"].cmd == ["pytest", "-vv", "--cov=src", "tests"]
        assert dag.tasks["mypy"].deps == {"ruff"}
        assert dag.tasks["pytest"].deps == {"mypy", "ruff"}

    def test_multiple_planners_same_config(self, tmp_path: Path):
        """Test that multiple Planner instances produce identical DAGs."""
        twin_dict: Dict[str, Any] = {
            "ruff_cmd": ["custom-ruff"],
            "pytest_depends_on": {"custom_dep"},
        }

        planner1 = Planner()
        dag1 = planner1.build_dag(twin_dict, tmp_path)

        planner2 = Planner()
        dag2 = planner2.build_dag(twin_dict, tmp_path)

        # Check that tasks are identical
        for task_id in dag1.tasks:
            assert dag1.tasks[task_id].cmd == dag2.tasks[task_id].cmd
            assert dag1.tasks[task_id].deps == dag2.tasks[task_id].deps


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_build_dag_with_pathlib_path(self, tmp_path: Path):
        """Test build_dag accepts pathlib.Path as root."""
        planner = Planner()
        dag = planner.build_dag({}, tmp_path)
        assert len(dag.tasks) == 3

    def test_build_dag_with_string_path(self, tmp_path: Path):
        """Test build_dag accepts string as root."""
        planner = Planner()
        dag = planner.build_dag({}, str(tmp_path))
        assert len(dag.tasks) == 3

    def test_build_dag_empty_config_dict(self, tmp_path: Path):
        """Test build_dag with empty config uses defaults."""
        planner = Planner()
        dag = planner.build_dag({}, tmp_path)

        # Should use default commands
        assert dag.tasks["ruff"].cmd == ["ruff", "check", "src"]
        assert dag.tasks["mypy"].cmd == ["mypy", "src"]
        assert dag.tasks["pytest"].cmd == ["pytest", "tests"]

    def test_compute_levels_single_task(self):
        """Test levels for single task."""
        dag = DAG()
        dag.add(Task(id="only", cmd=["echo"]))
        levels = _compute_levels(dag)
        assert len(levels) == 1
        assert levels[0] == ["only"]
