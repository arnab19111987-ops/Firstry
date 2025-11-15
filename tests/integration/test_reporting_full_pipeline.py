from types import SimpleNamespace
from firsttry.reports import summary as summary_mod
from firsttry.reporting import tty, html


def test_reporting_render_summary_end_to_end(tmp_path):
    # Build a minimal fake summary dict
    fake_summary = {
        "results": {
            "pytest": {"status": "ok", "message": "All tests passed"},
            "ruff": {"status": "ok", "message": "Lint clean"},
        }
    }

    # Render TTY (fallback path - no rich)
    tty_out = None
    # Call the summary renderer; should not raise
    summary_mod.render_summary(fake_summary)

    # HTML write: use object-like results mapping to hit attribute access branch
    dummy = SimpleNamespace(status="ok", duration_ms=5, cache_status="hit-local")
    results = {"pytest": dummy}
    html.write_html_report(tmp_path, results, out="report.html")

    html_path = tmp_path / "report.html"
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")
    assert "FirstTry Report" in content
