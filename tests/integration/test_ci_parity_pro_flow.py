import os
from types import SimpleNamespace

import firsttry.cli as cli


def test_ci_parity_pro_flow_minimal(tmp_path, monkeypatch, capsys):
    # Minimal repo
    (tmp_path / "foo.py").write_text("def test_dummy():\n    assert True\n", encoding="utf-8")

    # Env to simulate pro tier
    monkeypatch.setenv("FIRSTTRY_TIER", "pro")
    monkeypatch.setenv("FIRSTTRY_LICENSE_KEY", "dummy-pro-key")
    monkeypatch.setenv("FT_SEND_TELEMETRY", "0")

    # Stub ci_runner.main which cmd_ci -> cmd_pre_commit -> ci_runner.main calls
    def fake_ci_main(argv):
        print("[fake-ci] parity flow invoked")
        return 0

    # Patch the ci_runner in the cli module
    monkeypatch.setattr(cli, "ci_runner", SimpleNamespace(main=fake_ci_main))

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        rc = cli.cmd_ci()
    finally:
        os.chdir(cwd)

    assert rc == 0
