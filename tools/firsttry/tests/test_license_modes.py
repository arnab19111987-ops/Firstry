import pytest


def test_license_mode_default_offline(monkeypatch):
    # Import inside the test so the autouse fixture's reload produces the
    # same module object used by the validator (avoids multiple class objects
    # for LicenseError when tests reload modules).
    monkeypatch.delenv("FIRSTTRY_LICENSE_CHECK_MODE", raising=False)
    from firsttry.license_guard import LicenseError, _validate_license_max_security

    # This should only call offline path; invalid key should raise LicenseError
    with pytest.raises(LicenseError):
        _validate_license_max_security("invalid-key", "pro")


def test_license_mode_unknown(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_LICENSE_CHECK_MODE", "weird")
    from firsttry.license_guard import LicenseError, _validate_license_max_security

    with pytest.raises(LicenseError):
        _validate_license_max_security("dummy", "pro")
