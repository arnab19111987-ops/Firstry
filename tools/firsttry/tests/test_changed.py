import types

from firsttry.changed import filter_python, get_changed_files


def test_filter_python():
    files = ["a.py", "b.ts", "c.py", "README.md"]
    assert filter_python(files) == ["a.py", "c.py"]


def test_get_changed_files_monkeypatch(monkeypatch):
    def fake_run(args, check, stdout, stderr, text):
        ns = types.SimpleNamespace()
        ns.returncode = 0
        # git output may be normalized to repository-relative paths (e.g. "firsttry/cli.py")
        # or include the tools path depending on how the package is installed. Accept either.
        ns.stdout = "tools/firsttry/firsttry/cli.py\nREADME.md\n"
        ns.stderr = ""
        return ns

    monkeypatch.setattr("firsttry.changed.run", fake_run)
    out = get_changed_files("HEAD")

    # expected both paths from the fake stdout to be present
    assert "tools/firsttry/firsttry/cli.py" in out or "firsttry/cli.py" in out
    assert "README.md" in out

    # deterministic: should already be sorted and deduped
    assert out == sorted(dict.fromkeys(out))
