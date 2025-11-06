"""FIRSTTRY_SECURITY_CONTEXT: test-only

This test intentionally monkeypatches subprocess.exec and exercises dynamic exec
behaviour required by the runner contract. It's intentionally noisy for security scanners.
"""

import subprocess
import types

from firsttry import runners


def test__exec_respects_runtime_monkeypatch(monkeypatch, tmp_path):
    """Contract test:
    _exec() must call subprocess.run dynamically,
    NOT a cached snapshot taken at import time.

    Why this matters:
    - Our other tests monkeypatch subprocess.run
    - CI monkeypatches subprocess.run
    - If _exec binds a local alias at import time, patching breaks and tests get order-dependent.
    """
    captured = {}

    def fake_run(args, stdout, stderr, text, cwd=None):
        # simulate a "successful" subprocess exec
        captured["called"] = True
        captured["args"] = args
        return types.SimpleNamespace(
            returncode=0,
            stdout="ok",
            stderr="",
        )

    # Patch subprocess.run (not runners.run)
    monkeypatch.setattr(subprocess, "run", fake_run)

    # call _exec via its actual signature: (name, args, cwd)
    result = runners._exec("echo", ["echo", "hello"], cwd=tmp_path)

    # assertions
    assert captured.get("called") is True, "expected fake_run to be invoked"
    assert captured["args"] == ["echo", "hello"]
    assert result.ok is True
    assert result.stdout == "ok"
    assert result.stderr == ""
    assert result.cmd == tuple(["echo", "hello"])
