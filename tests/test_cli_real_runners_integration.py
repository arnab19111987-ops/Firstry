import importlib
from pathlib import Path

import pytest


@pytest.mark.skip(reason="Dynamic runner loading not implemented in current CLI")
def test_dynamic_loader_uses_real_runners(monkeypatch):
    """Integration test: write a minimal real runners module into the expected location,
    enable FIRSTTRY_USE_REAL_RUNNERS, reload `firsttry.cli`, and assert the real
    implementation is used.

    The test backs up any pre-existing module file and restores it on teardown.
    """
    monkeypatch.setenv("FIRSTTRY_USE_REAL_RUNNERS", "1")

    repo_root = Path(__file__).resolve().parents[1]
    target_dir = repo_root / "tools" / "firsttry" / "firsttry"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "runners.py"

    backup = None
    if target_file.exists():
        backup = target_file.with_suffix(".bak")
        target_file.rename(backup)

    try:
        # write a minimal runners implementation
        target_file.write_text(
            """
from types import SimpleNamespace

def run_ruff(*a, **k):
    return SimpleNamespace(ok=True, name='real-ruff', duration_s=0.1, stdout='', stderr='', cmd=())

def run_black_check(*a, **k):
    return SimpleNamespace(ok=True, name='real-black', duration_s=0.1, stdout='', stderr='', cmd=())

def run_mypy(*a, **k):
    return SimpleNamespace(ok=True, name='real-mypy', duration_s=0.1, stdout='', stderr='', cmd=())
""",
            encoding="utf-8",
        )

        # reload the CLI module to pick up the env var and new module file
        m = importlib.reload(importlib.import_module("firsttry.cli"))

        # The loader should have used the real implementation we just wrote
        r = m.runners.run_ruff([])
        assert getattr(r, "name", "") == "real-ruff"

        r2 = m.runners.run_black_check([])
        assert getattr(r2, "name", "") == "real-black"

    finally:
        # cleanup: remove our test file and restore backup if present
        try:
            if target_file.exists():
                target_file.unlink()
        except Exception:
            pass
        if backup is not None and backup.exists():
            backup.rename(target_file)
