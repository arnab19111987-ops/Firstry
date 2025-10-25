from firsttry.license import require_license


def test_require_license_blocks_when_missing(monkeypatch):
    # monkeypatch load_cached_license() to simulate "no license"
    from firsttry import license as lic_mod

    def fake_load_none():
        return None

    monkeypatch.setattr(lic_mod, "load_cached_license", fake_load_none)

    try:
        require_license()
    except SystemExit as e:
        assert e.code == 3
    else:
        raise AssertionError("require_license() did not block without license")
