from firsttry.config.schema import load_config


def test_precedence_env_over_local(monkeypatch, tmp_path):
    (tmp_path / "firsttry.toml").write_text("[policy]\nno_network=false\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FIRSTTRY_NO_NETWORK", "1")
    cfg = load_config()
    assert cfg.policy.no_network is True
