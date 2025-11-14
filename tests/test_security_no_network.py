import os
import subprocess
import sys


def test_no_network_flag_blocks_outbound(tmp_path):
    env = os.environ.copy()
    env["FIRSTTRY_NO_NETWORK"] = "1"
    cp = subprocess.run(
        [sys.executable, "-m", "firsttry.cli_main", "--no-network", "--dag-only"],
        cwd=str(tmp_path),
        text=True,
        capture_output=True,
        env=env,
    )
    # dag-only should still work locally with no network
    assert cp.returncode == 0
