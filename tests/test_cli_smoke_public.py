import subprocess
import sys
import json
from pathlib import Path


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    """
    Helper: run `python -m firsttry.cli <args...>` and capture output.
    Fails test immediately if returncode != 0.
    """
    cmd = [sys.executable, "-m", "firsttry.cli", *args]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    # We don't assert here because we also test failure modes.
    return proc


def test_doctor_runs_without_crash(tmp_path, monkeypatch):
    """
    Core safety promise:
    - 'firsttry doctor --json' should run without traceback
    - output should be valid JSON
    - exit code should be 0
    """
    # Some commands read env / cwd. Make sure we sandbox cwd:
    monkeypatch.chdir(tmp_path)

    proc = run_cli(["doctor", "--json"])
    assert proc.returncode == 0, f"doctor failed:\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}"

    # Ensure it produced valid JSON
    data = json.loads(proc.stdout)

    # Sanity keys we expect (customize if needed based on your real doctor output)
    # We are NOT asserting exact values; only shape.
    assert "checks" in data
    assert isinstance(data["checks"], list)


def test_list_gates_shows_expected_gates():
    """
    User-facing contract:
    'firsttry run --list' should exit 0 and mention coverage gate.
    """
    proc = run_cli(["run", "--list"])
    assert proc.returncode == 0, f"run --list failed:\n{proc.stderr}"

    # check for a known gate phrase you advertise publicly, like 'coverage'
    combined = proc.stdout + "\n" + proc.stderr
    assert "coverage" in combined.lower()
    assert "80" in combined  # expecting 80% coverage gate to be advertised
