from pathlib import Path
from unittest.mock import patch

from firsttry.runners.pytest import PytestRunner


def test_pytest_runner_receives_timeout_arg(tmp_path: Path):
    runner = PytestRunner()
    # create a tiny tests dir
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "tests/test_ok.py").write_text("def test_ok():\n    assert True\n")

    called = {}

    def fake_run(cmd, cwd=None, capture_output=True, text=True, timeout=None):
        called.update({"cmd": cmd, "cwd": cwd, "timeout": timeout})
        class P:
            returncode = 0
            stdout = ""
            stderr = ""
        return P()

    with patch("subprocess.run", side_effect=fake_run):
        rr = runner.run(tmp_path, ["tests/test_ok.py"], [], timeout_s=7)
    # rr is a RunResult; assert status and that subprocess.run got timeout
    assert rr.status == "ok"
    assert called.get("timeout") == 7
