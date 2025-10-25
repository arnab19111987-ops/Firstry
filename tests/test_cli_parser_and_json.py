from __future__ import annotations

import io
import json
import sys


from firsttry.cli import build_parser, cmd_mirror_ci


def test_cli_mirror_ci_parses_basic(tmp_path):
    parser = build_parser()
    ns = parser.parse_args(["mirror-ci", "--root", str(tmp_path)])
    # dry-run mode, no --run, no --json
    assert getattr(ns, "root")
    assert getattr(ns, "run") is False
    assert getattr(ns, "json") is False


def test_cli_mirror_ci_json_and_license_env(monkeypatch, tmp_path):
    """
    Simulate `mirror-ci --run --json` with only env key set.
    """

    fake_summary = {
        "ok": True,
        "results": [
            {
                "job": "qa",
                "step": "lint",
                "cmd": "ruff check .",
                "status": "success",
                "returncode": 0,
                "stdout": "clean\n",
                "stderr": "",
            }
        ],
    }

    # monkeypatch the pro runner
    import firsttry.pro_features as pro_features

    monkeypatch.setattr(
        pro_features,
        "run_ci_steps_locally",
        lambda plan, license_key=None: fake_summary,
    )

    # Set env license key, but DO NOT pass --license-key
    monkeypatch.setenv("FIRSTTRY_LICENSE_KEY", "ENV-KEY-123")

    parser = build_parser()
    ns = parser.parse_args(
        [
            "mirror-ci",
            "--root",
            str(tmp_path),
            "--run",
            "--json",
        ]
    )

    # Capture stdout of cmd_mirror_ci
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)

    exit_code = cmd_mirror_ci(ns)
    assert exit_code == 0

    out = buf.getvalue().strip()
    # Should be valid JSON
    data = json.loads(out)
    assert data["ok"] is True
    assert data["results"][0]["status"] == "success"
    assert data["results"][0]["cmd"] == "ruff check ."

    # Cleanup env var for safety
    monkeypatch.delenv("FIRSTTRY_LICENSE_KEY", raising=False)


def test_cli_mirror_ci_json_and_license_arg(monkeypatch, tmp_path):
    """
    Passing --license-key should override env var.
    """

    captured = {}

    def fake_runner(plan, license_key=None):
        # record what license key the CLI passed through
        captured["payload"] = license_key
        return {"ok": True, "results": []}

    import firsttry.pro_features as pro_features

    monkeypatch.setattr(pro_features, "run_ci_steps_locally", fake_runner)

    # BOTH env var and arg are set; arg should win
    monkeypatch.setenv("FIRSTTRY_LICENSE_KEY", "ENV-KEY-123")

    parser = build_parser()
    ns = parser.parse_args(
        [
            "mirror-ci",
            "--root",
            str(tmp_path),
            "--run",
            "--json",
            "--license-key",
            "ARG-KEY-999",
        ]
    )

    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)

    exit_code = cmd_mirror_ci(ns)
    assert exit_code == 0

    # make sure license precedence is correct
    assert captured["payload"]  # not empty
    assert "ARG-KEY-999" in str(captured["payload"])

    # cleanup
    monkeypatch.delenv("FIRSTTRY_LICENSE_KEY", raising=False)
