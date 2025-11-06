import shutil
import sys
from pathlib import Path

import pytest

from firsttry.planner.dag import Plan
from firsttry.planner.dag import Task
from firsttry.run_swarm import run_plan

pytestmark = pytest.mark.skipif(
    not (shutil.which("ruff") and shutil.which("mypy") and shutil.which("pytest")),
    reason="ruff/mypy/pytest CLIs must be on PATH",
)


def _write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_cache_hits_and_changed_only(tmp_path: Path, monkeypatch):
    # keep pytest lean
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

    repo = tmp_path
    # tiny mypy-clean module + pytest file
    _write(repo / "src/ft_demo/math.py", "def add(a: int, b: int) -> int:\n    return a + b\n")
    _write(repo / "tests/test_ok.py", "def test_ok():\n    assert True\n")

    # run inside tmp repo; allow local imports if any
    monkeypatch.chdir(repo)
    sys.path.insert(0, str(repo))

    # plan: ruff+mypy on the module, pytest on the single test
    plan = Plan()
    plan.tasks["ruff:demo"] = Task(
        id="ruff:demo",
        check_id="ruff",
        targets=["src/ft_demo/math.py"],
        flags=[],
        deps=set(),
    )
    plan.tasks["mypy:demo"] = Task(
        id="mypy:demo",
        check_id="mypy",
        targets=["src/ft_demo/math.py"],
        flags=[],
        deps=set(),
    )
    plan.tasks["pytest:smoke"] = Task(
        id="pytest:smoke",
        check_id="pytest",
        targets=["tests/test_ok.py"],
        flags=["-q"],
        deps=set(),
    )

    # COLD: all should run and succeed
    res1 = run_plan(repo, plan, use_remote_cache=False, workers=2)
    for k, v in res1.items():
        assert v.status == "ok", f"{k} failed on cold run: {getattr(v, 'stderr', '')}"

    # WARM: all should be cached (hit-local or hit-remote)
    res2 = run_plan(repo, plan, use_remote_cache=False, workers=2)
    for k, v in res2.items():
        cs = getattr(v, "cache_status", None)
        # Some TaskResult implementations put the cache marker into `status`
        if cs is None:
            cs = getattr(v, "status", None)
        assert cs in ("hit-local", "hit-remote"), f"{k} not cached on warm run"

    # CHANGE ONLY pytest input → pytest re-runs, ruff/mypy stay cached
    _write(repo / "tests/test_ok.py", "def test_ok():\n    assert 1+1==2\n")
    res3 = run_plan(repo, plan, use_remote_cache=False, workers=2)
    p_cs = getattr(res3["pytest:smoke"], "cache_status", None) or getattr(
        res3["pytest:smoke"],
        "status",
        None,
    )
    m_cs = getattr(res3["mypy:demo"], "cache_status", None) or getattr(
        res3["mypy:demo"],
        "status",
        None,
    )
    r_cs = getattr(res3["ruff:demo"], "cache_status", None) or getattr(
        res3["ruff:demo"],
        "status",
        None,
    )

    # pytest may report 'ok' when it actually re-ran and passed, or use a
    # cache marker like 'miss-run' / None depending on the runner impl.
    assert p_cs in (None, "miss-run", "ok")
    assert m_cs in ("hit-local", "hit-remote")
    assert r_cs in ("hit-local", "hit-remote")
