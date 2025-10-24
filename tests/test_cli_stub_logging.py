import importlib
import logging


def test_runner_stubs_emit_debug_logs(caplog):
    caplog.set_level(logging.DEBUG, logger="firsttry.cli")

    m = importlib.import_module("firsttry.cli")

    # Call a couple of stubbed runners
    r1 = m.runners.run_ruff(["file1.py"])
    r2 = m.runners.run_black_check(["file1.py"])

    # Ensure they returned harmless OK objects
    assert getattr(r1, "ok", False) is True
    assert getattr(r2, "ok", False) is True

    # Verify debug logs were emitted by the stub factory
    messages = [rec.getMessage() for rec in caplog.records]
    assert any("runners.stub ruff called" in m for m in messages)
    assert any("runners.stub black-check called" in m for m in messages)
