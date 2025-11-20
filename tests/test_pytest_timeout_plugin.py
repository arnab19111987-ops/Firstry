import pytest


@pytest.mark.timeout(1)
def test_pytest_timeout_plugin_is_active():
    # trivial work; should not hit timeout
    assert True
