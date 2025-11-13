import types

from click.testing import CliRunner

from firsttry import license_cache
from firsttry.cli import main


def test_cli_runs_when_license_ok(monkeypatch):
    # Ensure any on-disk license cache is cleared so the test's monkeypatch
    # controls the license behavior reliably even when run as part of the
    # full test suite (order-dependent caches caused intermittent failures).
    license_cache.clear_cache()
    # Also set env-backend values so the default assert_license() implementation
    # will validate successfully even if some code path bypasses the monkeypatch.
    monkeypatch.setenv("FIRSTTRY_LICENSE_BACKEND", "env")
    monkeypatch.setenv("FIRSTTRY_LICENSE_KEY", "devkey")
    monkeypatch.setenv("FIRSTTRY_LICENSE_ALLOW", "pro")
    # Make license checker return ok & features
    monkeypatch.setattr(
        "firsttry.cli.assert_license",
        lambda: (True, ["featX"], "cache"),
    )
    # Also patch other common assert_license entrypoints defensively so that
    # tests are robust even if other modules call the cache backend directly.
    monkeypatch.setattr(
        "firsttry.license_cache.assert_license",
        lambda: (True, ["featX"], "cache"),
        raising=False,
    )
    monkeypatch.setattr(
        "firsttry.license.assert_license",
        lambda: (True, ["featX"], "cache"),
        raising=False,
    )

    # Stub all runners to OK so the CLI completes with exit 0
    ok = types.SimpleNamespace(
        ok=True,
        name="ok",
        duration_s=0.0,
        stdout="",
        stderr="",
        cmd=("x",),
    )
    monkeypatch.setattr("firsttry.cli.runners.run_ruff", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.run_black_check", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.run_mypy", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.run_pytest_kexpr", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.run_coverage_xml", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.coverage_gate", lambda *a, **k: ok)

    res = CliRunner().invoke(
        main,
        ["run", "--gate", "pre-commit", "--require-license"],
        # catch_exceptions=False,  # uncomment to see raw traceback in pytest
    )

    if res.exit_code != 0:
        # Debugging output to help diagnose intermittent failure during full-suite runs
        print("DEBUG: cli_license_ok failed!")
        print("exit_code:", res.exit_code)
        print("output:\n", res.output)
        if res.exception:
            print("exception:", repr(res.exception))

    assert res.exit_code == 0
    assert "License ok" in res.output
