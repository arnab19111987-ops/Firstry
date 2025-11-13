import json
import subprocess
import sys


def test_dag_only_smoke():
    cp = subprocess.run([sys.executable, "-m", "firsttry.cli", "--dag-only"], capture_output=True, text=True)
    assert cp.returncode == 0
    # should output JSON; ensure it parses
    json.loads(cp.stdout)
