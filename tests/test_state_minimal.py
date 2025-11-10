from firsttry import state


def test_save_and_load_last_run(tmp_path, monkeypatch):
    # Point module-level paths to a temp dir so we don't touch the real home
    tmp_dir = tmp_path / "firsttry_home"
    monkeypatch.setattr(state, "_FIRSTTRY_DIR", tmp_dir)
    monkeypatch.setattr(state, "_LAST_RUN_PATH", tmp_dir / "last_run.json")

    assert state.load_last_run() is None

    payload = {"ok": True, "value": 42}
    state.save_last_run(payload)

    loaded = state.load_last_run()
    assert isinstance(loaded, dict)
    assert loaded == payload


def test_load_last_run_handles_invalid_json(tmp_path, monkeypatch):
    tmp_dir = tmp_path / "firsttry_home"
    monkeypatch.setattr(state, "_FIRSTTRY_DIR", tmp_dir)
    monkeypatch.setattr(state, "_LAST_RUN_PATH", tmp_dir / "last_run.json")

    # create a bad JSON file
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "last_run.json").write_text("not-a-json")

    assert state.load_last_run() is None
