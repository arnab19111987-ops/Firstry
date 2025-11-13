from __future__ import annotations

from typing import Optional

import firsttry.runners as runners
from firsttry.planner.dag import Task


def _make_task(check_id: str, timeout_s: Optional[int]) -> Task:
    return Task(
        id=f"{check_id}:proj-a",
        check_id=check_id,
        targets=["."],
        flags=[],
        deps=frozenset(),
        timeout_s=timeout_s,
    )


def test_run_ruff_forwards_timeout(monkeypatch, tmp_path):
    called = {}

    def fake_run_command(cmd, cwd, timeout=None):
        called["cmd"] = cmd
        called["cwd"] = cwd
        called["timeout"] = timeout

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr(runners, "run_command", fake_run_command)

    task = _make_task("ruff", timeout_s=111)
    rc = runners.run_ruff(task.targets, cwd=str(tmp_path), timeout=task.timeout_s)

    assert rc.ok
    assert called["timeout"] == 111


def test_run_mypy_forwards_timeout(monkeypatch, tmp_path):
    called = {}

    def fake_run_command(cmd, cwd, timeout=None):
        called["timeout"] = timeout

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr(runners, "run_command", fake_run_command)

    task = _make_task("mypy", timeout_s=222)
    rc = runners.run_mypy(task.targets, cwd=str(tmp_path), timeout=task.timeout_s)

    assert rc.ok
    assert called["timeout"] == 222


def test_run_pytest_files_forwards_timeout(monkeypatch, tmp_path):
    called = {}

    def fake_run_command(cmd, cwd, timeout=None):
        called["timeout"] = timeout

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr(runners, "run_command", fake_run_command)

    task = _make_task("pytest", timeout_s=333)
    rc = runners.run_pytest_files(task.targets, cwd=str(tmp_path), timeout=task.timeout_s)

    assert rc.ok
    assert called["timeout"] == 333
