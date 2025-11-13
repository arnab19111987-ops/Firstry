from __future__ import annotations

import json

from click.testing import CliRunner

import firsttry.cli as cli


def test_cli_dag_only_outputs_valid_json_and_exits_zero():
    runner = CliRunner()
    # Use the Click group object defined in cli.py
    result = runner.invoke(cli.cli_app, ["--dag-only"])

    # Should exit cleanly
    assert result.exit_code == 0

    # Should output JSON
    out = result.output.strip()
    assert out, "Expected some output from --dag-only"

    data = json.loads(out)
    # Should contain a DAG-ish field
    assert "dag" in data or "nodes" in data or "tasks" in data
