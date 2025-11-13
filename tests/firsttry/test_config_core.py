from __future__ import annotations

from pathlib import Path

from firsttry.config import get_config, get_s3_settings, get_workflow_requires


def test_get_config_reads_firsttry_toml_only(tmp_path: Path, monkeypatch):
    cfg_file = tmp_path / "firsttry.toml"
    cfg_file.write_text(
        """
        [workflow]
        pytest = ["ruff", "mypy"]

        [remote]
        bucket = "proj-bucket"
        region = "eu-west-1"
        """,
        encoding="utf-8",
    )

    # Avoid picking up real user config
    monkeypatch.setenv("HOME", str(tmp_path))

    cfg = get_config(tmp_path)

    assert cfg.workflow_requires == {"pytest": ["ruff", "mypy"]}
    assert cfg.s3_bucket == "proj-bucket"
    assert cfg.s3_region == "eu-west-1"


def test_env_overrides_remote_settings(tmp_path: Path, monkeypatch):
    cfg_file = tmp_path / "firsttry.toml"
    cfg_file.write_text(
        """
        [remote]
        bucket = "proj-bucket"
        region = "eu-west-1"
        """,
        encoding="utf-8",
    )

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("FT_S3_BUCKET", "env-bucket")
    monkeypatch.setenv("FT_S3_REGION", "us-east-1")
    monkeypatch.setenv("FT_S3_PREFIX", "firsttry/")

    cfg = get_config(tmp_path)
    s3 = get_s3_settings(tmp_path)

    assert cfg.s3_bucket == "env-bucket"
    assert cfg.s3_region == "us-east-1"
    assert s3["prefix"] == "firsttry/"


def test_get_workflow_requires_returns_copy(tmp_path: Path, monkeypatch):
    cfg_file = tmp_path / "firsttry.toml"
    cfg_file.write_text(
        """
        [workflow]
        pytest = ["ruff", "mypy"]
        ruff = "mypy"
        """,
        encoding="utf-8",
    )

    monkeypatch.setenv("HOME", str(tmp_path))

    workflow = get_workflow_requires(tmp_path)
    assert workflow == {"pytest": ["ruff", "mypy"], "ruff": ["mypy"]}

    # Should be a copy, not live view
    workflow["pytest"].append("other")
    cfg2 = get_config(tmp_path)
    assert cfg2.workflow_requires == {"pytest": ["ruff", "mypy"], "ruff": ["mypy"]}
