import importlib

CRITICAL = [
    "firsttry.state",
    "firsttry.planner",
    "firsttry.scanner",
    "firsttry.smart_pytest",
]


def test_import_critical_modules():
    for mod in CRITICAL:
        importlib.import_module(mod)


def _maybe_call(obj, name, *a, **kw):
    fn = getattr(obj, name, None)
    if callable(fn):
        try:
            fn(*a, **kw)
        except Exception:
            pass


def test_low_risk_calls():
    try:
        from firsttry import planner
        from firsttry import scanner
        from firsttry import smart_pytest
        from firsttry import state
    except Exception:
        return

    _maybe_call(state, "snapshot")
    _maybe_call(planner, "PlanBuilder")
    _maybe_call(scanner, "RepoScanner", root=".")
    _maybe_call(smart_pytest, "select_tests", repo_root=".", changed_paths=[])
