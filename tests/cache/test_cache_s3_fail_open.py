"""
Test S3 cache fail-open behavior with forced boto3 errors.

This module tests that S3Cache gracefully handles boto3 ClientError exceptions
by failing open (returning None for get, silently continuing for put) rather
than crashing the application.
"""

from typing import Any

import pytest
from botocore.exceptions import ClientError

# Import guard for optional moto dependency
mock_aws: Any = None
HAS_MOTO = False
try:
    from moto import mock_aws

    HAS_MOTO = True
except ImportError:

    def _noop_decorator(func):
        return func

    mock_aws = _noop_decorator

pytestmark = pytest.mark.skipif(not HAS_MOTO, reason="moto not installed")


@pytest.mark.skipif(not HAS_MOTO, reason="moto not available for S3 testing")
@mock_aws
def test_fail_open_on_client_error(monkeypatch):
    """
    Test that S3Cache fails open when boto3 operations raise ClientError.

    This test:
    1. Creates an S3Cache instance with valid environment configuration
    2. Patches the underlying boto3 S3 client to raise ClientError on operations
    3. Verifies that put() operations don't raise exceptions
    4. Verifies that get() operations return None (cache miss) instead of crashing

    This proves the fail-open behavior for AWS access errors, network issues, etc.
    """
    import boto3

    from firsttry.cache.s3 import S3Cache

    # Create mock S3 bucket
    bucket = "ft-cache-tests"
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket)

    # Set minimal environment for S3Cache construction
    monkeypatch.setenv("FT_S3_BUCKET", bucket)
    monkeypatch.setenv("FT_S3_PREFIX", "ci")

    cache = S3Cache.from_env()
    assert cache is not None, "S3Cache should be created with valid env config"

    # Force boto3 ClientError on all operations
    def boom_get_object(**kwargs):  # noqa: ARG001
        """Simulate AWS access denied on GetObject operation."""
        raise ClientError(
            error_response={"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            operation_name="GetObject",
        )

    def boom_put_object(**kwargs):  # noqa: ARG001
        """Simulate AWS access denied on PutObject operation."""
        raise ClientError(
            error_response={"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            operation_name="PutObject",
        )

    # Patch the S3 client to force errors
    monkeypatch.setattr(cache.s3, "get_object", boom_get_object, raising=True)
    monkeypatch.setattr(cache.s3, "put_object", boom_put_object, raising=True)

    # Test 1: put() should not raise exceptions (fail open)
    test_data = {"hello": "world", "test": "data"}
    cache.put("test-key", test_data)  # Should not raise

    # Test 2: get() should return None (cache miss) rather than crash
    result = cache.get("test-key")
    assert result is None, "get() should return None on ClientError (fail open)"

    # Test 3: Verify behavior with different error codes
    def boom_network_error(**kwargs):  # noqa: ARG001
        """Simulate network timeout error."""
        raise ClientError(
            error_response={"Error": {"Code": "RequestTimeout", "Message": "Request timeout"}},
            operation_name="GetObject",
        )

    monkeypatch.setattr(cache.s3, "get_object", boom_network_error, raising=True)

    result = cache.get("another-key")
    assert result is None, "get() should return None on network errors (fail open)"


@pytest.mark.skipif(not HAS_MOTO, reason="moto not available for S3 testing")
@mock_aws
def test_fail_open_on_serialization_error(monkeypatch):
    """
    Test that S3Cache fails open when JSON serialization fails.

    This covers edge cases where the cache data itself is problematic.
    """
    import boto3

    from firsttry.cache.s3 import S3Cache

    # Create mock S3 bucket
    bucket = "ft-cache-tests"
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket)

    # Set up cache
    monkeypatch.setenv("FT_S3_BUCKET", bucket)
    monkeypatch.setenv("FT_S3_PREFIX", "ci")

    cache = S3Cache.from_env()
    assert cache is not None

    # Test putting non-serializable data (should fail gracefully)
    class NonSerializable:
        pass

    non_serializable_data = {"obj": NonSerializable()}

    # This should not raise - fail open on serialization error
    cache.put("bad-key", non_serializable_data)

    # Verify we can still operate normally afterward
    cache.put("good-key", {"valid": "data"})


if __name__ == "__main__":
    # Allow running this test file directly for development
    pytest.main([__file__, "-v"])
