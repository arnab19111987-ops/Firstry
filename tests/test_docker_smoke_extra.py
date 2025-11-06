import builtins
import io

import pytest

import firsttry.docker_smoke as ds


def test_run_docker_smoke_ok(monkeypatch):
    # Make health check pass
    monkeypatch.setattr(ds, "check_health", lambda: True)
    # Capture stdout
    buf = io.StringIO()
    monkeypatch.setattr(
        builtins,
        "print",
        lambda *a, **k: buf.write(" ".join(map(str, a)) + "\n"),
    )

    ds.run_docker_smoke()
    out = buf.getvalue()
    assert "Docker smoke plan:" in out
    assert "Docker smoke OK" in out


def test_run_docker_smoke_fail(monkeypatch):
    monkeypatch.setattr(ds, "check_health", lambda: False)
    with pytest.raises(RuntimeError):
        ds.run_docker_smoke()
