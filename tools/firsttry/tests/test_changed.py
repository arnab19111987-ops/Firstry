from firsttry.changed import get_changed_files, filter_python
import types


def test_filter_python():
    files = ["a.py", "b.ts", "c.py", "README.md"]
    assert filter_python(files) == ["a.py", "c.py"]


def test_get_changed_files_monkeypatch(monkeypatch):
    def fake_run(args, check, stdout, stderr, text):
        ns = types.SimpleNamespace()
        ns.returncode = 0
        ns.stdout = "tools/firsttry/firsttry/cli.py\nREADME.md\n"
        ns.stderr = ""
        return ns

    monkeypatch.setattr("firsttry.changed.run", fake_run)
    out = get_changed_files("HEAD")
    assert "tools/firsttry/firsttry/cli.py" in out
