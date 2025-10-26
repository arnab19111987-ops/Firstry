from importlib import reload

from app import licensing as lic


def test_parse_feature_blob_edgecases():
    assert lic._parse_feature_blob("") == []
    assert lic._parse_feature_blob("a|b||c") == ["a", "b", "c"]


def test_load_key_store_parsing(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_KEYS", "ABC,PRO:feat1|feat2,TRIAL:trial||x,,BLANK:")
    reload(lic)
    # KEYS is module global set at import; re-import for update
    from app.licensing import KEYS

    assert KEYS["ABC"] == []
    assert KEYS["PRO"] == ["feat1", "feat2"]
    assert KEYS["TRIAL"] == ["trial", "x"]
    assert KEYS["BLANK"] == []


def test_verify_direct(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_KEYS", "AAA,BBB:feat")
    m = reload(lic)
    # Unknown product
    ok, reason, feats = m.verify("other", "AAA")
    assert ok is False and "unknown" in reason

    ok2, reason2, feats2 = m.verify("firsttry", "BBB")
    assert ok2 is True and feats2 == ["feat"]
