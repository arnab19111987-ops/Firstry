import pytest, os


def pytest_configure(config):
    config.addinivalue_line("markers", "flaky: quarantined test")
