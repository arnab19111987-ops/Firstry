from firsttry.pro_features import normalize_license


def test_normalize_license_dict_plan_and_features():
    payload = {
        "plan": "pro",
        "features": ["ci-mirror", "quickfix", "pg-drift"],
        "seats": 5,
    }
    norm = normalize_license(payload)
    assert norm["plan"] == "pro"
    assert "ci-mirror" in norm["features"]
    assert "quickfix" in norm["features"]
    assert "pg-drift" in norm["features"]


def test_normalize_license_legacy_list_only():
    payload = ["ci-mirror", "quickfix"]
    norm = normalize_license(payload)
    # legacy list implies fallback plan "free"
    assert norm["plan"] == "free"
    assert "ci-mirror" in norm["features"]
    assert "quickfix" in norm["features"]


def test_normalize_license_missing_plan_defaults_free():
    payload = {
        "features": ["a", "b"],
    }
    norm = normalize_license(payload)
    assert norm["plan"] == "free"
    assert norm["features"] == ["a", "b"]
