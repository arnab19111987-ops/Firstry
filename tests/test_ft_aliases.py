"""
Test the ft CLI alias system.
"""

import subprocess
import sys


def test_ft_help():
    """ft with no args should show help"""
    result = subprocess.run(
        [sys.executable, "-m", "firsttry.cli_aliases"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Usage: " in result.stdout
    assert "lite" in result.stdout
    assert "doctor" in result.stdout
    assert "doctor-checks" in result.stdout


def test_ft_lite_constructs_correct_command(monkeypatch, tmp_path):
    """ft lite should construct the right command"""
    import firsttry.cli_aliases

    # Mock subprocess.run to capture the command
    captured_cmd = []

    def mock_run(cmd):
        captured_cmd.append(cmd)

        # Mock successful return
        class MockProc:
            returncode = 0

        return MockProc()

    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("sys.argv", ["ft", "lite"])

    # Change to tmp dir to avoid polluting workspace
    monkeypatch.chdir(tmp_path)

    try:
        firsttry.cli_aliases.main()
    except SystemExit as e:
        # Should exit 0
        assert e.code == 0

    # Check the command was correct
    assert len(captured_cmd) == 1
    cmd = captured_cmd[0]
    assert "-m" in cmd
    assert "firsttry" in cmd
    assert "run" in cmd
    assert "fast" in cmd
    assert "--tier" in cmd
    assert "free-lite" in cmd
    assert "--report-json" in cmd
    assert "--report-schema" in cmd
    assert "2" in cmd


def test_ft_doctor_checks_constructs_correct_command(monkeypatch, tmp_path):
    """ft doctor-checks should call doctor with checks"""
    import firsttry.cli_aliases

    captured_cmd = []

    def mock_run(cmd):
        captured_cmd.append(cmd)

        class MockProc:
            returncode = 0

        return MockProc()

    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("sys.argv", ["ft", "doctor-checks"])
    monkeypatch.chdir(tmp_path)

    try:
        firsttry.cli_aliases.main()
    except SystemExit as e:
        assert e.code == 0

    cmd = captured_cmd[0]
    assert "doctor" in cmd
    # Ensure both checks present
    assert cmd.count("--check") >= 2
    assert "report-json" in cmd
    assert "telemetry" in cmd


def test_ft_dash_constructs_correct_command(monkeypatch, tmp_path):
    """ft dash should construct the right command"""
    import firsttry.cli_aliases

    captured_cmd = []

    def mock_run(cmd):
        captured_cmd.append(cmd)

        class MockProc:
            returncode = 0

        return MockProc()

    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("sys.argv", ["ft", "dash"])
    monkeypatch.chdir(tmp_path)

    try:
        firsttry.cli_aliases.main()
    except SystemExit as e:
        assert e.code == 0

    cmd = captured_cmd[0]
    assert "inspect" in cmd
    assert "dashboard" in cmd
    assert "--json" in cmd


def test_ft_lock_constructs_correct_command(monkeypatch, tmp_path):
    """ft lock should filter locked checks"""
    import firsttry.cli_aliases

    captured_cmd = []

    def mock_run(cmd):
        captured_cmd.append(cmd)

        class MockProc:
            returncode = 0

        return MockProc()

    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("sys.argv", ["ft", "lock"])
    monkeypatch.chdir(tmp_path)

    try:
        firsttry.cli_aliases.main()
    except SystemExit as e:
        assert e.code == 0

    cmd = captured_cmd[0]
    assert "inspect" in cmd
    assert "report" in cmd
    assert "--filter" in cmd
    assert "locked=true" in cmd


def test_ft_extra_flags_passed_through(monkeypatch, tmp_path):
    """Extra flags should be passed to underlying command"""
    import firsttry.cli_aliases

    captured_cmd = []

    def mock_run(cmd):
        captured_cmd.append(cmd)

        class MockProc:
            returncode = 0

        return MockProc()

    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("sys.argv", ["ft", "lite", "--show-report", "--send-telemetry"])
    monkeypatch.chdir(tmp_path)

    try:
        firsttry.cli_aliases.main()
    except SystemExit as e:
        assert e.code == 0

    cmd = captured_cmd[0]
    assert "--show-report" in cmd
    assert "--send-telemetry" in cmd
