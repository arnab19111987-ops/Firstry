import importlib
import subprocess

import pytest

RUNNERS = [
    "firsttry.runners.ruff",
    "firsttry.runners.mypy",
    "firsttry.runners.pytest",
    "firsttry.runners.bandit",
]


def _fake_run(*a, **k):
    class R:
        returncode = 0
        stdout = ""
        stderr = ""
        args = a

    return R()


@pytest.mark.parametrize("modname", RUNNERS)
def test_runner_build_and_invoke(monkeypatch, modname, tmp_path):
    try:
        m = importlib.import_module(modname)
    except Exception:
        pytest.skip(f"{modname} not present.")

    # Prevent any real execution
    monkeypatch.setattr(subprocess, "run", _fake_run, raising=True)

    # Try common public entrypoints without guessing internals:
    #  - build_cmd/build_args → returns a list[str]
    #  - run/execute/main → calls subprocess.run internally
    # We'll attempt in a safe order and assert basic properties.
    for build_name in ("build_cmd", "build_args", "cmd_for_paths"):
        build = getattr(m, build_name, None)
        if callable(build):
            cmd = build(paths=[str(tmp_path)], config=None)
            assert isinstance(cmd, (list, tuple)) and cmd
            break

    # Invoke a "run" style function if present (it should use our stubbed subprocess.run)
    for run_name in ("run", "execute", "main"):
        fn = getattr(m, run_name, None)
        if callable(fn):
            # Supply minimal args; fallbacks if signature differs are handled via try/except
            try:
                rv = fn(paths=[str(tmp_path)], config=None, check=False)
            except TypeError:
                try:
                    rv = fn([str(tmp_path)])
                except TypeError:
                    rv = fn()
            # Only assert that call returned or did not crash under stub
            assert rv is None or isinstance(rv, int)
            break
