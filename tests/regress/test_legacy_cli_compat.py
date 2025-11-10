import subprocess
import sys
import pytest


def run(args):
    return subprocess.run([sys.executable, "-m", "firsttry"] + args, capture_output=True, text=True)


def test_legacy_gate_translates_or_warns():
    p = run(["run", "--gate", "ruff", "--dry-run"])
    # PRE-FIX: likely "invalid choice: 'ruff'".
    # POST-FIX: either runs (translated) or prints a clear deprecation message.
    combined = (p.stdout or "") + (p.stderr or "")
    assert ("invalid choice" not in combined.lower()) or ("deprecated" in combined.lower())
