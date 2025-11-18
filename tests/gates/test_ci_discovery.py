from __future__ import annotations

import pathlib
import textwrap

import pytest

from firsttry.gates.ci_discovery import _dump_ci_mirror_toml, discover_ci

try:
    import yaml  # type: ignore[import]
except Exception:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


@pytest.mark.skipif(yaml is None, reason="pyyaml not installed")
def test_discover_ci_from_simple_workflow(tmp_path: pathlib.Path) -> None:
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    wf = wf_dir / "ci.yml"
    wf.write_text(
        textwrap.dedent(
            """
            name: CI
            on: [push]
            jobs:
              tests:
                runs-on: ubuntu-latest
                steps:
                  - name: Install deps
                    run: echo "install"
                  - name: Run tests
                    run: pytest
              lint:
                runs-on: ubuntu-latest
                steps:
                  - name: Run ruff
                    run: ruff src
            """
        ).lstrip(),
        encoding="utf8",
    )

    ci_cfg = discover_ci(tmp_path)
    assert ci_cfg.jobs
    assert ci_cfg.plans

    job_names = sorted(ci_cfg.jobs.keys())
    assert any("ci.yml:tests" in j for j in job_names)
    assert any("ci.yml:lint" in j for j in job_names)

    toml_text = _dump_ci_mirror_toml(ci_cfg)
    assert "[jobs." in toml_text
    assert "[plans." in toml_text
    assert "pytest" in toml_text
    assert "ruff src" in toml_text
