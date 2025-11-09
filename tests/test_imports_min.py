def test_imports():
    import importlib

    # simple smoke: ensure modules load
    assert importlib.import_module("firsttry.state")
    assert importlib.import_module("firsttry.planner")
    assert importlib.import_module("firsttry.scanner")
    assert importlib.import_module("firsttry.smart_pytest")
