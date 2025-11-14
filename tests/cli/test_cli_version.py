import subprocess
import sys


def test_firsttry_version_cli():
    proc = subprocess.run(
        [sys.executable, "-m", "firsttry.cli", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    # Should exit 0 and print a one-line version
    assert proc.returncode == 0
    out = proc.stdout.strip().splitlines()
    assert out, "No output from --version"
    assert out[0].startswith("firsttry-run ") or out[0].startswith("FirstTry ")
