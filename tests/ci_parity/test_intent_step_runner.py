from __future__ import annotations

from pathlib import Path
from typing import Dict

import subprocess

from firsttry.ci_parity.step_runner import run_step_with_fallback
from firsttry.ci_parity.intents import INTENT_REGISTRY, CommandIntent


class DummyCompleted:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode


def test_run_step_with_fallback_prefers_firsttry(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_run(cmd, shell, cwd, env, text):
        calls.append(cmd)
        return DummyCompleted(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    # ensure intent exists
    INTENT_REGISTRY["tests_fast"] = CommandIntent(
        key="tests_fast",
        firsttry_cmd="firsttry pytest --fast",
        raw_cmd="pytest -q -k 'not slow and not e2e'",
        ecosystem="python",
    )

    step: Dict[str, str] = {
        "id": "tests",
        "intent": "tests_fast",
        "run": "pytest -q -k 'not slow and not e2e'",
    }

    res = run_step_with_fallback(step, cwd=tmp_path, env={})

    assert res.used_source == "firsttry"
    assert "firsttry pytest --fast" in calls[0]
    assert not res.fallback_used
    assert res.returncode == 0


def test_run_step_with_fallback_uses_raw_if_firsttry_fails(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_run(cmd, shell, cwd, env, text):
        calls.append(cmd)
        # First call (FirstTry) fails, second (raw) passes
        if len(calls) == 1:
            return DummyCompleted(returncode=1)
        return DummyCompleted(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    INTENT_REGISTRY["tests_fast"] = CommandIntent(
        key="tests_fast",
        firsttry_cmd="firsttry pytest --fast",
        raw_cmd="pytest -q -k 'not slow and not e2e'",
        ecosystem="python",
    )

    step: Dict[str, str] = {
        "id": "tests",
        "intent": "tests_fast",
        "run": "pytest -q -k 'not slow and not e2e'",
    }

    res = run_step_with_fallback(step, cwd=tmp_path, env={})

    assert res.used_source == "raw"
    assert res.fallback_used
    assert "firsttry pytest --fast" in calls[0]
    assert "pytest -q -k 'not slow and not e2e'" in calls[1]
    assert res.returncode == 0
