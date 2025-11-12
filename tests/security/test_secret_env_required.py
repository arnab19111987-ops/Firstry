"""Test that FIRSTTRY_SHARED_SECRET is required in production mode."""
import sys

import pytest


def test_secret_env_required_in_production(monkeypatch):
    """Verify that missing FIRSTTRY_SHARED_SECRET raises in production."""
    # Clear all secret-related env vars
    monkeypatch.delenv("FIRSTTRY_SHARED_SECRET", raising=False)
    monkeypatch.delenv("FT_SHARED_SECRET", raising=False)
    
    # Simulate production environment
    monkeypatch.delenv("FIRSTTRY_ENV", raising=False)
    monkeypatch.setenv("CI", "true")
    
    # Remove module from cache to force reimport
    if "firsttry.license" in sys.modules:
        del sys.modules["firsttry.license"]
    
    # Should raise RuntimeError in production without secret
    with pytest.raises(RuntimeError, match="FIRSTTRY_SHARED_SECRET.*required in production"):
        pass


def test_secret_dev_fallback_warns(monkeypatch):
    """Verify that dev mode uses fallback but warns."""
    # Clear secret env var
    monkeypatch.delenv("FIRSTTRY_SHARED_SECRET", raising=False)
    monkeypatch.delenv("FT_SHARED_SECRET", raising=False)
    
    # Simulate development environment
    monkeypatch.setenv("FIRSTTRY_ENV", "development")
    
    # Remove module from cache to force reimport
    if "firsttry.license" in sys.modules:
        del sys.modules["firsttry.license"]
    
    # Should warn but not raise
    with pytest.warns(UserWarning, match="FIRSTTRY_SHARED_SECRET not set.*insecure dev fallback"):
        import firsttry.license
        assert firsttry.license.DEFAULT_SHARED_SECRET == "dev-only-insecure-fallback"


def test_secret_from_env(monkeypatch):
    """Verify that FIRSTTRY_SHARED_SECRET from env is used."""
    # Set a custom secret
    test_secret = "test-secret-for-unit-tests-min-32-chars-long"
    monkeypatch.setenv("FIRSTTRY_SHARED_SECRET", test_secret)
    
    # Remove module from cache to force reimport
    if "firsttry.license" in sys.modules:
        del sys.modules["firsttry.license"]
    
    # Should use env var without warnings
    import firsttry.license
    assert firsttry.license.DEFAULT_SHARED_SECRET == test_secret
