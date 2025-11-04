"""Ensure CLI doctor uses monkeypatchable gather/render paths and prints report."""

from tests.cli_utils import run_cli
import types


def test_cli_doctor_uses_monkeypatched_report(monkeypatch):
    import firsttry.doctor as doctor_mod

    fake_report = types.SimpleNamespace(
        passed_count=2,
        total_count=2,
        checks=[1, 2],
        summary_line=lambda: "2/2 checks passed (100%).",
    )

    def fake_gather(runner=None):
        return fake_report

    def fake_render(rep):
        return "# FirstTry Doctor Report\nHealth: OK\n"

    monkeypatch.setattr(doctor_mod, "gather_checks", fake_gather)
    monkeypatch.setattr(doctor_mod, "render_report_md", fake_render)

    code, out, err = run_cli(["doctor"])
    assert code == 0
    assert "FirstTry Doctor Report" in out
