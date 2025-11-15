import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """
    Helper to run 'python -m firsttry.cli ...' under the repo root.
    """
    return subprocess.run(
        [sys.executable, "-m", "firsttry.cli", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_cli_top_level_help():
    proc = run_cli("--help")
    assert proc.returncode == 0
    out = proc.stdout.lower()
    # Should mention at least one of the core commands.
    assert "mirror-ci" in out or "pre-commit" in out or "ci-parity" in out


def test_cli_version_subcommand_or_flag():
    proc_flag = run_cli("--version")
    # Either this path works …
    if proc_flag.returncode == 0 and proc_flag.stdout.strip():
        assert "firsttry" in proc_flag.stdout.lower()
        return

    # … or fall back to the version subcommand.
    proc_cmd = run_cli("version")
    assert proc_cmd.returncode == 0
    assert "firsttry" in proc_cmd.stdout.lower()
