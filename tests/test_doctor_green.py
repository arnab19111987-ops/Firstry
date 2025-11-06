"""Test that FirstTry doctor (CI parity guard) passes on clean repo.
Enforces CI-Green Guarantee: all critical systems green.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest


def test_doctor_green_enforced():
    """FirstTry doctor must be green on a clean repo.
    Doctor prints health line like "Health: **5/5 checks passed" or "✓ All systems OK".
    If doctor fails, CI parity guarantee is broken.
    """
    env = dict(os.environ)
    result = subprocess.run(
        [sys.executable, "-m", "firsttry.cli", "doctor"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    # Check for success indicators
    has_success = (
        "checks passed" in result.stdout.lower()
        or "all systems" in result.stdout.lower()
        or result.returncode == 0
    )

    # Check for failure indicators
    has_failure = ("health" in result.stdout.lower() and result.returncode != 0) or (
        "error" in result.stderr.lower() and result.returncode != 0
    )

    if not has_success or has_failure:
        pytest.fail(
            f"FirstTry doctor failed (CI parity guarantee broken):\n"
            f"Return code: {result.returncode}\n"
            f"Stdout:\n{result.stdout}\n"
            f"Stderr:\n{result.stderr}",
        )
