"""Test that FIRSTTRY_SHARED_SECRET is required in production mode."""
import subprocess
import sys

import pytest


def test_secret_env_required_in_production():
    """Verify that missing FIRSTTRY_SHARED_SECRET raises in production."""
    # Run in subprocess to avoid module import pollution
    code = """
import os
import sys

# Simulate production: CI=true, no FIRSTTRY_SHARED_SECRET
os.environ['CI'] = 'true'
os.environ.pop('FIRSTTRY_SHARED_SECRET', None)
os.environ.pop('FIRSTTRY_ENV', None)

try:
    import firsttry.license
    sys.exit(1)  # Should not reach here
except RuntimeError as e:
    if 'FIRSTTRY_SHARED_SECRET' in str(e) and 'required in production' in str(e):
        sys.exit(0)  # Expected error
    else:
        print(f"Wrong error: {e}", file=sys.stderr)
        sys.exit(2)
"""
    
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    
    assert (
        result.returncode == 0
    ), f"Expected RuntimeError in production, got: {result.stderr}"


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
