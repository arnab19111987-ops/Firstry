from __future__ import annotations

import subprocess
import types

import pytest

import firsttry.gates as gates


def _fake_success_cmd(cmd: str):
    Fake = types.SimpleNamespace
    return Fake(args=cmd, returncode=0, stdout="ok\n", stderr="")


def _fake_fail_cmd(cmd: str):
    Fake = types.SimpleNamespace
    return Fake(args=cmd, returncode=1, stdout="nope\n", stderr="boom\n")


@pytest.mark.parametrize("return_ok", [True, False])
def test_gate_runner_handles_subprocess(monkeypatch, tmp_path, return_ok):
    """
    Ensure gates.run_gate handles subprocess outputs and reports pass/fail.
    """

    def fake_run(*args, **kwargs):
        # Accept either list or str command
        cmd = args[0] if args else kwargs.get("cmd", "cmd")
        if return_ok:
            return _fake_success_cmd(cmd if isinstance(cmd, str) else "cmd")
        else:
            return _fake_fail_cmd(cmd if isinstance(cmd, str) else "cmd")

    monkeypatch.setattr(subprocess, "run", fake_run)

    results, overall_ok = gates.run_gate("pre-commit")

    assert isinstance(results, list)
    assert isinstance(overall_ok, bool)

    saw_fail = False
    for entry in results:
        # After JSON contract refactor, entries are dict-like
        assert isinstance(entry, dict)
        assert "gate" in entry
        assert "ok" in entry
        assert "returncode" in entry
        assert "stdout" in entry
        assert "stderr" in entry

        status = entry.get("status")
        # Validate returncode semantics depending on status
        if status == "PASS":
            # Passing tools should report returncode 0
            assert entry.get("returncode") == 0
        elif status == "SKIPPED":
            # Skipped checks may not have return codes
            assert entry.get("returncode") is None
        elif status == "FAIL":
            # Failing tools should report a non-zero returncode (unless exception path)
            rc = entry.get("returncode")
            if rc is not None:
                assert rc != 0
            saw_fail = True

    if return_ok:
        assert overall_ok is True
        assert saw_fail is False
    else:
        assert overall_ok is False
        # At least one gate should have reported failure when we forced failures
        assert saw_fail is True


def test_gate_runner_json_serializable(monkeypatch, tmp_path):
    """
    The gate results should be convertible to JSON-able structures.
    """

    def fake_run(*args, **kwargs):
        Fake = types.SimpleNamespace
        return Fake(args=args, returncode=0, stdout="all good\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    results, overall_ok = gates.run_gate("pre-commit")

    try:
        import json

        json.dumps({"results": results, "ok": overall_ok})
    except TypeError as exc:
        pytest.fail(f"Gate output not JSON serializable: {exc}")


def test_gate_runner_handles_exception(monkeypatch, tmp_path):
    """
    If subprocess.run raises unexpectedly, the gate runner should catch
    the exception and return a failing, structured result rather than
    letting the exception bubble up.
    """

    def boom_run(*args, **kwargs):
        raise RuntimeError("simulated tool crash")

    monkeypatch.setattr(subprocess, "run", boom_run)

    results, overall_ok = gates.run_gate("pre-commit")

    assert isinstance(results, list)
    assert overall_ok is False

    # There should be at least one failing gate entry with the crash message
    found = False
    for entry in results:
        assert isinstance(entry, dict)
        if not entry.get("ok"):
            details = entry.get("details") or ""
            if "simulated tool crash" in details:
                found = True
                break

    assert found, "Expected a failing gate entry containing the exception message"
