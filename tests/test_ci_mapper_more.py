import textwrap

from firsttry import ci_mapper


def test_rewrite_run_cmd_python3_and_pytest(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_PYTHON", "/usr/bin/py311")
    cmd = "python3 -m pip install -r reqs.txt && pytest -q"
    out = ci_mapper.rewrite_run_cmd(cmd)
    assert out.startswith("/usr/bin/py311 -m pip install")
    assert "/usr/bin/py311 -m pytest -q" in out


def test_ci_mapper_env_inheritance_legacy_steps(tmp_path):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    yaml_text = textwrap.dedent(
        """
        name: LegacyEnv
        jobs:
          build:
            env:
              A: "1"
            steps:
              - name: Install
                run: echo install
                env:
                  B: "2"
              - name: Test
                run: echo test
        """,
    )
    (wf_dir / "legacy.yml").write_text(yaml_text, encoding="utf-8")

    plan = ci_mapper.build_ci_plan(str(tmp_path))
    wf = plan.get("workflows")[0]
    steps = wf["jobs"][0]["steps"]
    s0, s1 = steps
    assert s0["env"]["A"] == "1" and s0["env"]["B"] == "2"
    assert s1["env"]["A"] == "1"
