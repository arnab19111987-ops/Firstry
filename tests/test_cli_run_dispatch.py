def test_main_routes_run_to_cmd_run(monkeypatch):
    """Ensure top-level `firsttry run` dispatches to cmd_run (DAG path).

    We replace `cmd_run` with a stub and call `main(['run', 'free-lite'])` to
    verify the stub is invoked with the remaining argv (['free-lite']).
    """
    import firsttry.cli as cli

    called = {}

    def fake_cmd_run(argv=None):
        called['argv'] = argv
        return 123

    monkeypatch.setattr(cli, 'cmd_run', fake_cmd_run)

    # Use a valid top-level mode choice that the main parser accepts
    res = cli.main(['run', 'auto'])

    assert res == 123
    assert called['argv'] == ['auto']
