import subprocess
import sys
import re
import os


def test_free_lite_no_finalizer_and_locked_not_timed(tmp_path):
    env = os.environ.copy()
    cmd = [sys.executable, "-m", "firsttry", "run", "--tier", "free-lite", "--debug-phases", "--show-report"]
    p = subprocess.run(cmd, text=True, capture_output=True, env=env)
    out = (p.stdout or "") + "\n" + (p.stderr or "")
    assert "Event loop is closed" not in out
    if "Locked" in out or "🔒" in out:
        assert not re.search(r"tim(e|ing).*(locked|🔒)", out, re.IGNORECASE)
