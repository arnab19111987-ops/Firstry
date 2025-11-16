from __future__ import annotations

from dataclasses import FrozenInstanceError

import firsttry.executor.dag as exec_dag
from firsttry.planner.dag import Task


def test_task_is_frozen_and_has_timeout():
    task = Task(
        id="pytest:proj-a",
        check_id="pytest",
        targets=["tests/"],
        flags=["-q"],
        deps=frozenset(),
        timeout_s=42,
    )

    # FrozenInstanceError on mutation
    try:
        task.id = "changed"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("Task should be frozen (immutable)")


def test_call_runner_with_timeout_passes_timeout_kw(monkeypatch, tmp_path):
    received = {}

    def fake_runner(task: Task, cwd: str, timeout: int | None = None) -> int:
        received["task"] = task
        received["cwd"] = cwd
        received["timeout"] = timeout
        return 0

    task = Task(
        id="pytest:proj-a",
        check_id="pytest",
        targets=["tests/"],
        flags=["-q"],
        deps=frozenset(),
        timeout_s=123,
    )

    rc = exec_dag._call_runner_with_timeout(
        runner=fake_runner,
        task=task,
        cwd=str(tmp_path),
    )

    assert rc == 0
    assert received["task"] is task
    assert received["cwd"] == str(tmp_path)
    assert received["timeout"] == 123


def test_call_runner_without_timeout_kw_still_works(monkeypatch, tmp_path):
    received = {}

    def fake_runner_no_timeout(task: Task, cwd: str) -> int:
        received["task"] = task
        received["cwd"] = cwd
        return 7

    task = Task(
        id="ruff:proj-a",
        check_id="ruff",
        targets=["src/"],
        flags=[],
        deps=frozenset(),
        timeout_s=321,
    )

    rc = exec_dag._call_runner_with_timeout(
        runner=fake_runner_no_timeout,
        task=task,
        cwd=str(tmp_path),
    )

    assert rc == 7
    assert received["task"] is task
    assert received["cwd"] == str(tmp_path)
    # No timeout kw, so nothing to assert about timeout
