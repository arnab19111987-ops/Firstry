import subprocess
import sys
from pathlib import Path


def test_mypy_passes():
    """
    Run mypy against the firsttry package.
    This locks in typed, professional-looking surfaces for customers.
    """
    repo_root = Path.cwd()
    pkg_dir = repo_root / "firsttry"
    assert pkg_dir.is_dir(), "firsttry package should exist"

    res = subprocess.run(
        [sys.executable, "-m", "mypy", str(pkg_dir)],
        capture_output=True,
        text=True,
    )

    if res.returncode != 0:
        # show stdout+stderr to make debugging easy in CI
        raise AssertionError(
            f"mypy failed:\nSTDOUT:\n{res.stdout}\n\nSTDERR:\n{res.stderr}"
        )
