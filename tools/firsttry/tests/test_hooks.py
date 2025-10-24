from pathlib import Path
from firsttry.hooks import install_pre_commit_hook


def test_install_pre_commit_hook(tmp_path: Path, monkeypatch):
    # fake a .git dir
    g = tmp_path / ".git" / "hooks"
    g.mkdir(parents=True)
    hook = install_pre_commit_hook(tmp_path)
    assert hook.exists()
    assert "FirstTry" in hook.read_text(encoding="utf-8")
    assert hook.stat().st_mode & 0o111  # executable
