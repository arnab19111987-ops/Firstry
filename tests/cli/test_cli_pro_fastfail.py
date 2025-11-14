import os
import subprocess
import sys


def run_cli(args):
    env = os.environ.copy()
    # Ensure no accidental overrides
    env.pop("FIRSTTRY_FORCE_TIER", None)
    env.pop("FIRSTTRY_TIER", None)
    env.pop("FIRSTTRY_LICENSE_KEY", None)
    return subprocess.run(
        [sys.executable, "-m", "firsttry.cli"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=10,
        env=env,
    )

def test_fastfail_when_pro_requested_without_license():
    proc = run_cli(["run", "--tier", "pro"])
    # Should exit quickly with non-zero (2) and show the guard message
    assert proc.returncode == 2
    out = proc.stdout
    assert "Tier 'pro' is locked" in out
    assert "FIRSTTRY_LICENSE_KEY" in out
    assert "firsttry.com/pricing" in out
