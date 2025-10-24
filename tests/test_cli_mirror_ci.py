import io
import sys
from pathlib import Path
import textwrap

from firsttry.cli import build_parser


def test_cli_mirror_ci_dryrun(tmp_path, monkeypatch):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    yaml_text = textwrap.dedent(
        """
        name: CI
        on: [push]
        jobs:
          qa:
            runs-on: ubuntu-latest
            steps:
              - name: Echo hello
                run: echo "hi"
        """
    )
    (wf_dir / "ci.yml").write_text(yaml_text, encoding="utf-8")

    parser = build_parser()
    ns = parser.parse_args(["mirror-ci", "--root", str(tmp_path)])

    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)

    rc = ns.func(ns)
    assert rc == 0

    out = buf.getvalue()
    assert "Workflow: ci.yml" in out
    assert "Job: qa" in out
    assert 'echo "hi"' in out
