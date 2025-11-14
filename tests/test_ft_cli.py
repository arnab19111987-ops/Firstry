import pytest
from click.testing import CliRunner
import pytest
from click.testing import CliRunner

from firsttry import ft


def test_ft_local_runs_successfully():
    runner = CliRunner()
    result = runner.invoke(ft.main, ["local"])
    assert result.exit_code == 0


def test_ft_doctor_gated_for_free(monkeypatch):
    # ensure wrapper reports free
    monkeypatch.setattr("firsttry.tier.get_current_tier", lambda: "free")
    runner = CliRunner()
    result = runner.invoke(ft.main, ["doctor"])
    # Exit code 2 is gating
    assert result.exit_code == 2


def test_ft_doctor_allowed_for_pro(monkeypatch):
    monkeypatch.setattr("firsttry.tier.get_current_tier", lambda: "pro")
    runner = CliRunner()
    result = runner.invoke(ft.main, ["doctor"])
    assert result.exit_code == 0
