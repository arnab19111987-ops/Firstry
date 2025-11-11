def test_main_routes_run_to_cmd_run(monkeypatch):
    """Ensure top-level `firsttry run` dispatches to cmd_run (DAG path).

    We replace `cmd_run` with a stub and call `main(['run', 'pro'])` to
    verify the stub is invoked with the remaining argv (['pro']).
    """
    from firsttry import cli

    called = {}

    def fake_cmd_run(argv=None):
        called["argv"] = argv
        return 123

    monkeypatch.setattr(cli, "cmd_run", fake_cmd_run)

    # Use a tier that routes to cmd_run (not lite/strict variants)
    res = cli.main(["run", "pro"])

    assert res == 123
    assert called["argv"] == ["pro"]
