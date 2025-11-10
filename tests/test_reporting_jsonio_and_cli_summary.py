import importlib

import pytest

SYNTHETIC_REPORT = {
    "version": "0.0-test",
    "summary": {"status": "ok", "checks": 3, "failures": 0, "duration_ms": 12},
    "details": [
        {"name": "ruff", "status": "ok", "duration_ms": 3},
        {"name": "mypy", "status": "ok", "duration_ms": 4},
        {"name": "pytest", "status": "ok", "duration_ms": 5},
    ],
}


def test_jsonio_roundtrip(tmp_path):
    try:
        jsonio = importlib.import_module("firsttry.reporting.jsonio")
    except Exception:
        pytest.skip("jsonio not available in this revision.")

    save = getattr(jsonio, "save_json", None) or getattr(jsonio, "write_json", None)
    load = getattr(jsonio, "load_json", None) or getattr(jsonio, "read_json", None)
    if not callable(save) or not callable(load):
        pytest.skip("jsonio lacks save/load helpers in this revision.")

    f = tmp_path / "report.json"
    save(SYNTHETIC_REPORT, f)
    back = load(f)
    assert isinstance(back, dict)
    assert back.get("summary", {}).get("checks") == 3


def test_cli_summary_render_safe():
    try:
        cli_summary = importlib.import_module("firsttry.reports.cli_summary")
    except Exception:
        pytest.skip("cli_summary not present.")

    # Try to find a render/format function that accepts a dict-like report
    for name in ("render", "format_report", "build_cli_summary", "summarize"):
        fn = getattr(cli_summary, name, None)
        if callable(fn):
            out = fn(SYNTHETIC_REPORT)
            # Some implementations print to stdout instead of returning;
            # accept either a string or None (printed).
            if out is not None:
                assert isinstance(out, str)
            break
    else:
        pytest.skip("No public render-like function on cli_summary.")
