from __future__ import annotations

import io
import json
import sys

import pytest

from firsttry.cli import build_parser


def test_cli_gates_json_smoke(monkeypatch, tmp_path):
    import pytest

    pytest.skip("Legacy test disabled - functionality removed")


@pytest.mark.skip(
    reason="cmd_gates functionality has been removed in favor of new CLI structure",
)
def test_cmd_gates_json_output(monkeypatch, tmp_path):
    """CLI contract:
    cmd_gates with --json flag should produce parseable JSON on stdout
    and exit 1 if any gate failed.
    """
    fake_summary = {
        "ok": False,
        "results": [
            {
                "gate": "pre-commit",
                "ok": False,
                "status": "fail",
                "info": "ruff",
                "details": "lint errors",
                "returncode": 1,
                "stdout": "ruff said nope",
                "stderr": "",
            },
            {
                "gate": "pre-push",
                "ok": True,
                "status": "pass",
                "info": "mypy",
                "details": "clean",
                "returncode": 0,
                "stdout": "success",
                "stderr": "",
            },
        ],
    }

    import firsttry.gates as gates_mod

    monkeypatch.setattr(
        gates_mod,
        "run_all_gates",
        lambda repo_root: fake_summary,
    )

    parser = build_parser()
    ns = parser.parse_args(
        [
            "gates",
            "--root",
            str(tmp_path),
            "--json",
        ],
    )

    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)

    exit_code = cmd_gates(ns)

    # Should exit 1 because ok=False in fake_summary
    assert exit_code == 1

    out = buf.getvalue().strip()
    data = json.loads(out)

    assert data["ok"] is False
    assert len(data["results"]) == 2
    assert data["results"][0]["gate"] == "pre-commit"
    assert data["results"][0]["returncode"] == 1
    assert data["results"][1]["gate"] == "pre-push"
    assert data["results"][1]["ok"] is True
