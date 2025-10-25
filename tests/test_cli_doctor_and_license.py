# tests/test_cli_doctor_and_license.py
import types

from click.testing import CliRunner


def test_cli_doctor_uses_report(monkeypatch):
    # Import from the ROOT firsttry package (not tools/firsttry)
    import firsttry.cli as cli_mod

    fake_report = types.SimpleNamespace(
        passed_count=2,
        total_count=2,
        summary_line=lambda: "2/2 checks passed (100%).",
    )

    def fake_gather(runner=None):
        return fake_report

    def fake_render(rep):
        return "# FirstTry Doctor Report\nHealth: OK\n"

    monkeypatch.setattr("firsttry.doctor.gather_checks", fake_gather)
    monkeypatch.setattr("firsttry.doctor.render_report_md", fake_render)

    runner = CliRunner()
    result = runner.invoke(cli_mod.main, ["doctor"])

    assert "FirstTry Doctor Report" in result.output
    assert result.exit_code == 0  # all passed -> exit 0


def test_cli_doctor_exitcode_nonzero(monkeypatch):
    import firsttry.cli as cli_mod

    fake_report = types.SimpleNamespace(
        passed_count=1,
        total_count=2,
        summary_line=lambda: "1/2 checks passed (50%).",
    )

    def fake_gather(runner=None):
        return fake_report

    def fake_render(rep):
        return "# FirstTry Doctor Report\nHealth: BAD\n"

    monkeypatch.setattr("firsttry.doctor.gather_checks", fake_gather)
    monkeypatch.setattr("firsttry.doctor.render_report_md", fake_render)

    runner = CliRunner()
    result = runner.invoke(cli_mod.main, ["doctor"])
    assert result.exit_code == 1  # not all passed


def test_cli_license_verify_prints_status(monkeypatch):
    import firsttry.cli as cli_mod

    class FakeInfo:
        valid = True
        plan = "pro"
        expiry = "2099-01-01T00:00:00Z"

    def fake_verify(license_key, server_url, http_post):
        # assert we forward args
        assert license_key == "KEY123"
        assert server_url == "http://fake"
        return FakeInfo()

    monkeypatch.setattr("firsttry.license.verify_license", fake_verify)

    runner = CliRunner()
    result = runner.invoke(
        cli_mod.main,
        [
            "license",
            "verify",
            "--license-key",
            "KEY123",
            "--server-url",
            "http://fake",
        ],
    )

    assert "plan=pro" in result.output
    assert "valid=True" in result.output
    assert result.exit_code == 0


def test_cli_license_verify_nonvalid_exitcode(monkeypatch):
    import firsttry.cli as cli_mod

    class FakeInfo:
        valid = False
        plan = "free"
        expiry = None

    def fake_verify(license_key, server_url, http_post):
        return FakeInfo()

    monkeypatch.setattr("firsttry.license.verify_license", fake_verify)

    runner = CliRunner()
    result = runner.invoke(cli_mod.main, ["license", "verify"])
    assert result.exit_code == 1
