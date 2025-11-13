from __future__ import annotations

import firsttry.config as config


def test_get_workflow_requires_reads_project_toml(tmp_path, monkeypatch):
    proj_toml = tmp_path / "firsttry.toml"
    proj_toml.write_text(
        """
[workflow]
requires = ["ruff", "mypy"]
        """.strip(),
        encoding="utf-8",
    )

    # Point config at our temp project file
    monkeypatch.setattr(config, "PROJECT_TOML", proj_toml)
    # Reset cache
    monkeypatch.setattr(config, "_CONFIG_CACHE", None, raising=False)

    requires = config.get_workflow_requires()
    assert set(requires) == {"ruff", "mypy"}


def test_get_workflow_requires_handles_missing_section(tmp_path, monkeypatch):
    proj_toml = tmp_path / "firsttry.toml"
    proj_toml.write_text(
        """
[other]
foo = "bar"
        """.strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "PROJECT_TOML", proj_toml)
    monkeypatch.setattr(config, "_CONFIG_CACHE", None, raising=False)

    requires = config.get_workflow_requires()
    assert requires == []
