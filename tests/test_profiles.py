import pytest

from firsttry.profiles import get_profile, list_profiles


def test_list_profiles_has_core():
    names = list_profiles()
    assert "fast" in names
    assert "strict" in names
    assert "release" in names


def test_get_profile_known():
    p = get_profile("fast")
    assert p.name == "fast"
    assert isinstance(p.gates, list)
    assert "python:ruff" in p.gates


def test_get_profile_unknown():
    with pytest.raises(KeyError):
        get_profile("does-not-exist")
