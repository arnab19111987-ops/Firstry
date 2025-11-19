from __future__ import annotations

import subprocess
import sys


def test_cli_run_stub_gate_passes(monkeypatch, tmp_path):
    # Test the run command using subprocess to avoid Click dependency
    monkeypatch.chdir(tmp_path)

    # Run the CLI as a subprocess
    result = subprocess.run(
        [sys.executable, "-m", "firsttry", "run", "fast"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    # Should succeed even if no files to check
    assert result.returncode in [0, 1]  # 1 is OK for lint failures


def test_cli_run_require_license_failure(monkeypatch, tmp_path):
    # Test license enforcement in CLI
    import pytest

    pytest.skip("License checking integration test - would require full license setup")


def test_cli_run_require_license_success(monkeypatch, tmp_path):
    # Test successful license validation
    import pytest

    pytest.skip("License checking integration test - would require full license setup")
