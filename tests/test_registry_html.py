from pathlib import Path


def test_registry_has_all_checks():
    from firsttry.runners.registry import default_registry

    reg = default_registry()
    for k in ["ruff", "mypy", "pytest", "bandit", "npm-lint", "npm-test"]:
        assert k in reg, f"missing runner: {k}"


def test_html_files_written(tmp_path: Path):
    # write simple report.json and then call our simple html generator
    import json
    from pathlib import Path

    rdir = tmp_path
    rdir.mkdir(parents=True, exist_ok=True)
    report = {
        "checks": {
            "ruff:_root": {
                "name": "ruff:_root",
                "check_id": "ruff",
                "status": "ok",
                "duration_ms": 10,
            },
        },
    }
    p = rdir / ".firsttry"
    p.mkdir()
    (p / "report.json").write_text(json.dumps(report))
    # Use the local reporting html functions by loading module via path
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "htmlmod",
        str(Path("src/firsttry/reporting/html.py").resolve()),
    )
    if spec is None or spec.loader is None:
        raise ImportError("Could not load html.py module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["htmlmod"] = mod
    spec.loader.exec_module(mod)
    # Create fake TaskResult-like objects for write_html_report

    class R:
        pass

    r = R()
    r.status = "ok"  # type: ignore[attr-defined]
    r.duration_ms = 12  # type: ignore[attr-defined]
    mod.write_html_report(rdir, {"ruff:_root": r}, out=str(p / "report.html"))
    mod.write_html_dashboard(rdir, out=str(p / "dashboard.html"))
    assert (p / "report.html").exists()
    assert (p / "dashboard.html").exists()
