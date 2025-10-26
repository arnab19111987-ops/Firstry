import types

import firsttry.changed as ch


def _fake_proc(rc=0, out="", err=""):
    return types.SimpleNamespace(returncode=rc, stdout=out, stderr=err)


def test_filter_python_basic():
    assert ch.filter_python(["a.py", "b.txt", "c.pyc", "d.py"]) == ["a.py", "d.py"]


def test_get_changed_files_happy(monkeypatch):
    # Simulate git returning some files with dupes and double slashes
    def fake_run(args, check, stdout, stderr, text):
        assert args[:3] == ["git", "diff", "--name-only"]
        return _fake_proc(0, out="src/a.py\nREADME.md\nsrc//b.py\nsrc/a.py\n\n", err="")

    monkeypatch.setattr(ch, "run", fake_run)
    files = ch.get_changed_files("HEAD~1")
    assert files == ["README.md", "src/a.py", "src/b.py"]


def test_get_changed_files_git_missing(monkeypatch):
    def fake_run(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(ch, "run", fake_run)
    assert ch.get_changed_files() == []


def test_get_changed_files_nonzero(monkeypatch):
    def fake_run(*a, **k):
        return _fake_proc(1, out="", err="bad")

    monkeypatch.setattr(ch, "run", fake_run)
    assert ch.get_changed_files() == []
