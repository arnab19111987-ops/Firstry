import json

from firsttry import doctor as doc


class FakeRunner:
    def __init__(self, returncode=0, output="ok"):
        self.returncode = returncode
        self.output = output

    def run(self, cmd):
        return self.returncode, self.output


def test_gather_checks_all_pass():
    runner = FakeRunner(0, "all good")
    report = doc.gather_checks(runner=runner, parallel=False)
    assert report.passed_count == report.total_count
    assert report.score_pct == 100.0


def test_gather_checks_one_fail():
    runner = FakeRunner(1, "error")
    report = doc.gather_checks(runner=runner, parallel=False)
    assert report.passed_count < report.total_count


def test_gather_checks_parallel():
    runner = FakeRunner(0, "ok")
    report = doc.gather_checks(runner=runner, parallel=True)
    assert report.total_count > 0


def test_gather_checks_skip_all(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_DOCTOR_SKIP", "all")
    report = doc.gather_checks(runner=FakeRunner(), parallel=False)
    # All checks should be skipped with passed=True
    assert all(c.passed for c in report.checks)


def test_gather_checks_skip_specific(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_DOCTOR_SKIP", "pytest,ruff")
    report = doc.gather_checks(runner=FakeRunner(), parallel=False)
    skipped_names = [c.name for c in report.checks if "skipped" in c.output]
    assert "pytest" in skipped_names
    assert "ruff" in skipped_names


def test_render_report_md():
    checks = [
        doc.CheckResult("lint", True, "ok"),
        doc.CheckResult("types", False, "error: missing type", "add types"),
    ]
    report = doc.DoctorReport(checks, 1, 2, 50.0, ["fix: run mypy"])
    md = doc.render_report_md(report)
    assert "# FirstTry Doctor Report" in md
    assert "✅" in md
    assert "❌" in md
    assert "Quick Fix Suggestions" in md


def test_render_report_json():
    checks = [doc.CheckResult("test", True, "passed")]
    report = doc.DoctorReport(checks, 1, 1, 100.0, [])
    j = doc.render_report_json(report)
    data = json.loads(j)
    assert data["passed_count"] == 1
    assert data["score_pct"] == 100.0


def test_report_to_dict():
    checks = [doc.CheckResult("a", True, "good", "hint")]
    report = doc.DoctorReport(checks, 1, 1, 100.0, ["do this"])
    d = doc.report_to_dict(report)
    assert d["total_count"] == 1
    assert d["quickfixes"] == ["do this"]


def test_run_doctor_report_normal():
    report = doc.run_doctor_report(parallel=False)
    assert all(r.status == "ok" for r in report.results)
    assert report.warning is None


def test_run_doctor_report_skip_all(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_DOCTOR_SKIP", "all")
    report = doc.run_doctor_report()
    assert all(r.status == "skip" for r in report.results)
    assert report.warning is not None


def test_render_human():
    results = [
        doc.SimpleCheck("lint", "ok", "clean"),
        doc.SimpleCheck("types", "fail", "errors"),
    ]
    report = doc.SimpleDoctorReport(results, warning="some warning")
    human = doc.render_human(report)
    assert "WARNING: some warning" in human
    assert "lint: ok" in human
    assert "types: fail" in human


def test_render_json_simple():
    results = [doc.SimpleCheck("test", "ok", "passed")]
    report = doc.SimpleDoctorReport(results, None)
    j = doc.render_json(report)
    data = json.loads(j)
    assert data["results"][0]["name"] == "test"
    assert data["warning"] is None
