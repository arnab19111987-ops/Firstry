import textwrap


def test_find_unmapped_steps_detects_unmapped_action(tmp_path):
    workflows_root = tmp_path / ".github" / "workflows"
    workflows_root.mkdir(parents=True)
    wf = workflows_root / "fake.yml"
    wf.write_text(
        textwrap.dedent(
            """
        jobs:
          myjob:
            runs-on: ubuntu-latest
            steps:
              - uses: actions/does-not-exist@v1
    """
        )
    )

    mirror_dir = tmp_path / ".firsttry"
    mirror_dir.mkdir()
    mirror = mirror_dir / "ci_mirror.toml"
    mirror.write_text("jobs = []\n")

    from firsttry.ci_parity.unmapped import find_unmapped_steps

    unmapped = find_unmapped_steps(
        mirror_path=str(mirror), workflows_root=str(workflows_root)
    )
    assert any(u.job == "myjob" for u in unmapped)
    assert any("actions/does-not-exist" in u.step for u in unmapped)


def test_missing_job_reports_missing_mapping(tmp_path):
    workflows_root = tmp_path / ".github" / "workflows"
    workflows_root.mkdir(parents=True)
    wf = workflows_root / "another.yml"
    wf.write_text(
        textwrap.dedent(
            """
        jobs:
          unmapped_job:
            runs-on: ubuntu-latest
            steps:
              - run: echo hi
    """
        )
    )

    mirror_dir = tmp_path / ".firsttry"
    mirror_dir.mkdir()
    mirror = mirror_dir / "ci_mirror.toml"
    mirror.write_text("jobs = []\n")

    from firsttry.ci_parity.unmapped import find_unmapped_steps

    unmapped = find_unmapped_steps(
        mirror_path=str(mirror), workflows_root=str(workflows_root)
    )
    assert any(
        u.job == "unmapped_job" and "missing mirror mapping" in u.reason
        for u in unmapped
    )


def test_get_mirror_status_marks_missing_and_extra(tmp_path):
    # Create workflows dir with one workflow
    workflows_root = tmp_path / ".github" / "workflows"
    workflows_root.mkdir(parents=True)
    wf = workflows_root / "present.yml"
    wf.write_text("jobs:\n  a:\n    runs-on: ubuntu-latest\n")

    # Mirror contains an extra workflow entry and missing the present.yml
    mirror_dir = tmp_path / ".firsttry"
    mirror_dir.mkdir()
    mirror = mirror_dir / "ci_mirror.toml"
    mirror.write_text(
        textwrap.dedent(
            """
      [[jobs]]
      workflow = "absent.yml"
      job_id = "a"
    """
        )
    )

    from firsttry.ci_parity.mirror_status import get_mirror_status

    ms = get_mirror_status(mirror_path=str(mirror), workflows_root=str(workflows_root))
    assert not ms.is_fresh
    assert "present.yml" in ms.missing_workflows or isinstance(
        ms.missing_workflows, list
    )
    assert "absent.yml" in ms.extra_workflows
