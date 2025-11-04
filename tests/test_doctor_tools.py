from __future__ import annotations

import shutil



def test_doctor_tools_all_present(monkeypatch):
    # Simulate all tools present
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    from firsttry.doctor import doctor_tools_probe

    results, ok = doctor_tools_probe()
    assert ok is True
    assert all(v == "ok" for v in results.values())


def test_doctor_tools_some_missing(monkeypatch):
    # Simulate mypy missing
    def fake_which(name: str):
        if name == "mypy":
            return None
        return f"/usr/bin/{name}"

    monkeypatch.setattr(shutil, "which", fake_which)
    from firsttry.doctor import doctor_tools_probe

    results, ok = doctor_tools_probe()
    assert ok is False
    assert results.get("mypy") == "missing"
