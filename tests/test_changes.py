from pathlib import Path

import subprocess

from firsttry.changes import get_changed_files


def test_get_changed_files_when_none(tmp_path):
    files = get_changed_files(tmp_path, None)
    assert files == []


def test_get_changed_files_git_present(monkeypatch, tmp_path):
    def fake_co(cmd, cwd=None, text=None):
        return "a.py\ndir/b.py\n"

    monkeypatch.setattr(subprocess, "check_output", fake_co)
    files = get_changed_files(tmp_path, "HEAD~1")
    assert files == ["a.py", "dir/b.py"]
