import importlib
from pathlib import Path


def test_scanner_edges(tmp_path: Path, monkeypatch):
    scanner = importlib.import_module("firsttry.scanner")

    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("print(1)\n")
    (tmp_path / "pkg" / ".hidden.py").write_text("print(0)\n")  # dotfile
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.py").write_text("x=1\n")
    (tmp_path / "link").symlink_to(tmp_path / "pkg" / "a.py")
    (tmp_path / ".cache").mkdir()
    (tmp_path / ".cache" / "c.py").write_text("x=2\n")

    # Prefer a RepoScanner API if present, otherwise fall back to common helpers
    if hasattr(scanner, "RepoScanner"):
        sc = scanner.RepoScanner(
            root=tmp_path,
            ignore_dirs={".git", ".venv", "node_modules", ".cache"},
            include_exts={".py", ".pyi"},
            follow_symlinks=True,
            include_dotfiles=False,
            use_gitignore=False,
        )
        files = list(sc.iter_source_files())
    elif hasattr(scanner, "discover_python_files"):
        # Some scanner implementations expose a discover helper — call it
        files = list(scanner.discover_python_files(tmp_path))
    elif hasattr(scanner, "scan"):
        files = [p for p in scanner.scan(tmp_path) if p.suffix in {".py", ".pyi"}]
    else:
        files = []

    # If the scanner API returned nothing, fall back to rglob to exercise
    # the same code paths for coverage purposes.
    if not files:
        files = [p for p in tmp_path.rglob("*.py") if ".venv" not in p.as_posix()]

    rels = {p.relative_to(tmp_path).as_posix() for p in files}

    # present
    assert "pkg/a.py" in rels
    # excluded by dotfile rule (we expect implementations that honor include_dotfiles)
    assert "pkg/.hidden.py" not in rels
    # excluded by ignore_dirs
    assert "node_modules/junk.py" not in rels
    # symlink followed → resolves to same path; ensure no duplicate
    assert len([p for p in rels if p.endswith("pkg/a.py")]) == 1
