import importlib


def test_reporting_stack_imports():
    for m in [
        "firsttry.report",
        "firsttry.reporting",
        "firsttry.reporting.__init__",
        "firsttry.reporting.html",
        "firsttry.reporting.jsonio",
        "firsttry.reporting.renderer",
        "firsttry.reporting.tty",
        "firsttry.reports",
        "firsttry.reports.cli_summary",
        "firsttry.reports.detail",
        "firsttry.reports.summary",
        "firsttry.reports.tier_map",
        "firsttry.reports.ui",
    ]:
        importlib.import_module(m)
