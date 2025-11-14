from __future__ import annotations

from dataclasses import FrozenInstanceError

import firsttry.planner.dag as dag
import firsttry.runner.executor as executor


def test_task_is_frozen():
    task = dag.Task(
        id="t1",
        check_id="pytest",
        targets=["tests/"],
        flags=["-q"],
        deps=frozenset(),
        timeout_s=None,
    )

    # Mutations should not be allowed
    try:
        task.id = "t2"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("Task should be frozen (immutable)")


def test_get_effective_timeout_default():
    task = dag.Task(
        id="t1",
        check_id="pytest",
        targets=[],
        flags=[],
        deps=frozenset(),
        timeout_s=None,
    )

    timeout = executor.get_effective_timeout(task)
    assert timeout == executor.DEFAULT_TASK_TIMEOUT_S


def test_get_effective_timeout_respects_task_timeout():
    task = dag.Task(
        id="t1",
        check_id="pytest",
        targets=[],
        flags=[],
        deps=frozenset(),
        timeout_s=123,
    )

    timeout = executor.get_effective_timeout(task)
    assert timeout == 123


def test_run_task_passes_timeout_to_run_command(monkeypatch, tmp_path):
    called = {}

    def fake_run_command(cmd, cwd, timeout=None):
        called["cmd"] = cmd
        called["cwd"] = cwd
        called["timeout"] = timeout

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr(executor, "run_command", fake_run_command)

    task = dag.Task(
        id="t1",
        check_id="pytest",
        targets=["tests/"],
        flags=["-q"],
        deps=frozenset(),
        timeout_s=321,
    )

    rc = executor.run_task(task, cwd=str(tmp_path))
    assert rc == 0
    assert called["timeout"] == 321
