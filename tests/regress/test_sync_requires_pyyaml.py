import importlib
import subprocess
import sys
import pytest

@pytest.mark.skipif(importlib.util.find_spec("yaml") is not None, reason="PyYAML present")
def test_sync_graceful_message_when_pyyaml_missing():
    # Run in a subprocess to avoid importing ci_parser in this process.
    cmd = [sys.executable, "-m", "firsttry", "sync"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    # POST-FIX expect friendly message and non-zero exit
    assert p.returncode != 0
    combined = (p.stdout or "") + (p.stderr or "")
    assert "PyYAML" in combined or "firsttry[ci]" in combined or "CI parser unavailable" in combined
