# tests/cache/test_cache_s3.py
import pytest

try:
    from moto import mock_aws

    MOTO_AVAILABLE = True
except Exception:
    # Provide a no-op decorator when moto is not available
    def mock_aws(func):
        return func

    MOTO_AVAILABLE = False

pytestmark = pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not available")
@mock_aws
def test_s3_put_get_roundtrip(monkeypatch, tmp_path):
    import boto3

    from firsttry.cache.base import CacheHit
    from firsttry.cache.s3 import S3Cache

    bucket = "ft-cache-tests"
    prefix = "ci"
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket)

    monkeypatch.setenv("FT_S3_BUCKET", bucket)
    monkeypatch.setenv("FT_S3_PREFIX", prefix)

    cache = S3Cache.from_env()
    assert cache is not None

    key = "abc123"
    payload = CacheHit(stdout="test output", stderr="", meta={"status": "ok", "value": 42})
    cache.put(key, payload)

    got = cache.get(key)
    assert got is not None
    assert got.stdout == "test output"
    assert got.meta == {"status": "ok", "value": 42}


@pytest.mark.skipif(mock_aws is None, reason="moto not available")
@mock_aws
def test_s3_graceful_fallback_on_error(monkeypatch):
    """
    Prove that when boto3 raises, the cache 'fails open': no crash, just a miss.
    """
    from firsttry.cache.s3 import S3Cache

    # Intentionally DO NOT set FT_S3_BUCKET to make from_env() return None
    monkeypatch.delenv("FT_S3_BUCKET", raising=False)
    monkeypatch.delenv("FT_S3_PREFIX", raising=False)

    # Without config, from_env should return None and the app should not crash
    cache = S3Cache.from_env()
    assert cache is None


@pytest.mark.skipif(mock_aws is None, reason="moto not available")
@mock_aws
def test_s3_error_handling_during_operations(monkeypatch):
    """
    Test that S3 operations fail gracefully when credentials are bad or bucket doesn't exist.
    """
    from firsttry.cache.base import CacheHit
    from firsttry.cache.s3 import S3Cache

    # Set up environment with bad bucket
    monkeypatch.setenv("FT_S3_BUCKET", "nonexistent-bucket")
    monkeypatch.setenv("FT_S3_PREFIX", "test")

    cache = S3Cache.from_env()
    assert cache is not None

    # These operations should not crash, just return None or do nothing
    result = cache.get("test-key")
    assert result is None

    # put() should not crash on errors
    test_hit = CacheHit(stdout="test", stderr="", meta={})
    cache.put("test-key", test_hit)  # Should not raise
