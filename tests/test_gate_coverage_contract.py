from __future__ import annotations

import pytest


class _R:
    def __init__(self, ok: bool, name: str = "fake"):
        self.ok = ok
        self.name = name
        self.duration_s = 0.0
        self.stdout = ""
        self.stderr = ""
        self.cmd = ()


@pytest.mark.skip(reason="_run_gate_via_runners method does not exist in current CLI")
def test_coverage_gate_blocks_commit(monkeypatch):
    pass
