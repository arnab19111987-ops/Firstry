"""
Explicitly ensure the cache.s3 module behaves when boto3 isn’t installed by injecting a stub.
"""

import importlib
import sys
import types


def test_cache_s3_import_without_real_boto3(monkeypatch):
    # Replace any real boto3 with a very small stub
    fake_boto3 = types.ModuleType("boto3")

    class _Fake:
        def __getattr__(self, _):
            def _noop(*a, **k):
                return {}

            return _noop

    fake_boto3.client = lambda *a, **k: _Fake()
    sys.modules["boto3"] = fake_boto3

    m = importlib.import_module("firsttry.cache.s3")
    # If module exposes a symbol we can sanity-check, do it gently
    assert m is not None
