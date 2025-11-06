from __future__ import annotations

from pathlib import Path

from .graph import CodebaseTwin


def twin_path(repo_root: Path) -> Path:
    return repo_root / ".firsttry" / "twin.json"


def save_twin(repo_root: Path, twin: CodebaseTwin) -> None:
    p = twin_path(repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(twin.to_json())


def load_twin(repo_root: Path) -> CodebaseTwin | None:
    p = twin_path(repo_root)
    if not p.exists():
        return None
    return CodebaseTwin.from_json(p.read_text())
