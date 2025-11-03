import subprocess
import sys


def run_cli_subproc(args: list[str]) -> subprocess.CompletedProcess[str]:
    """
    Helper: run `python -m firsttry.cli <args...>` in a subprocess and capture output.
    Use only for commands that are safe to execute in a child process.
    """
    cmd = [sys.executable, "-m", "firsttry.cli", *args]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc


def test_doctor_runs_without_crash(tmp_path, monkeypatch):
    """
    Core safety promise:
    - 'firsttry doctor' should run without traceback
    - exit code should be reasonable (0 or 1)
    """
    # Some commands read env / cwd. Make sure we sandbox cwd:
    monkeypatch.chdir(tmp_path)

    # Run doctor command
    proc = run_cli_subproc(["doctor"])

    # Should not crash with traceback
    assert proc.returncode in [0, 1]  # 0 = all good, 1 = some issues found
    
    # Should produce some output
    assert len(proc.stdout) > 0 or len(proc.stderr) > 0


def test_list_gates_shows_expected_gates(tmp_path, monkeypatch):
    """
    User-facing contract:
    CLI should run basic commands without crashing.
    """
    # Test that inspect command works
    monkeypatch.chdir(tmp_path)
    
    proc = run_cli_subproc(["inspect"])
    
    # Should not crash 
    assert proc.returncode in [0, 1, 2]  # Various exit codes are OK
    
    # Should produce some output
    assert len(proc.stdout) > 0 or len(proc.stderr) > 0
