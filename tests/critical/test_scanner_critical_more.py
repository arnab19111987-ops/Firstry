from pathlib import Path

from firsttry.scanner import RepoScanner


def test_scanner_edges(tmp_path: Path, monkeypatch):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("print(1)\n")
    (tmp_path / "pkg" / ".hidden.py").write_text("print(0)\n")  # dotfile
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.py").write_text("x=1\n")
    (tmp_path / "link").symlink_to(tmp_path / "pkg" / "a.py")
    (tmp_path / ".cache").mkdir()
    (tmp_path / ".cache" / "c.py").write_text("x=2\n")

    sc = RepoScanner(
        root=tmp_path,
        ignore_dirs={".git", ".venv", "node_modules", ".cache"},
        include_exts={".py", ".pyi"},
        follow_symlinks=True,  # exercise follow branch
        include_dotfiles=False,  # exercise dotfile gate
        use_gitignore=False,  # if supported
    )
    files = list(sc.iter_source_files())
    rels = {p.relative_to(tmp_path).as_posix() for p in files}

    # present
    assert "pkg/a.py" in rels
    # excluded by dotfile rule
    assert "pkg/.hidden.py" not in rels
    # excluded by ignore_dirs
    assert "node_modules/junk.py" not in rels
    # symlink followed → resolves to same path; ensure no duplicate
    assert len([p for p in rels if p.endswith("pkg/a.py")]) == 1
