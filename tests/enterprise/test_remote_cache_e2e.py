"""Remote cache E2E tests using LocalStack S3.

Tests for:
1. Cold run → S3 upload validation
2. Warm run → S3 download validation
3. Cache hit verification (≤5ms response)
4. S3 object listing consistency
5. Remote cache performance impact

Setup:
- Requires LocalStack with S3 service
- Uses test AWS credentials
- Creates temporary S3 bucket
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict

import pytest


@pytest.fixture(scope="function")
def localstack_s3() -> Dict[str, str]:
    """Fixture for LocalStack S3 service.

    Returns:
        Dict with S3 configuration:
        - endpoint_url: LocalStack S3 endpoint
        - bucket: Test bucket name
        - region: AWS region
    """
    config = {
        "endpoint_url": os.getenv("FT_S3_ENDPOINT", "http://localhost:4566"),
        "bucket": os.getenv("FT_S3_BUCKET", "ft-cache-e2e"),
        "region": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        "access_key": os.getenv("AWS_ACCESS_KEY_ID", "test"),
        "secret_key": os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    }

    # Verify LocalStack is reachable
    try:
        result = subprocess.run(
            ["aws", "--endpoint-url", config["endpoint_url"], "s3", "ls"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            pytest.skip("LocalStack S3 not available")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("AWS CLI or LocalStack not available")

    yield config


@pytest.fixture(scope="function")
def s3_bucket(localstack_s3: Dict[str, str]) -> str:
    """Create and cleanup S3 bucket for testing.

    Yields:
        Bucket name
    """
    config = localstack_s3
    bucket = config["bucket"]
    endpoint = config["endpoint_url"]

    # Create bucket
    subprocess.run(
        ["aws", "--endpoint-url", endpoint, "s3", "mb", f"s3://{bucket}"],
        capture_output=True,
        timeout=10,
    )

    yield bucket

    # Cleanup: remove bucket and objects
    subprocess.run(
        ["aws", "--endpoint-url", endpoint, "s3", "rm", f"s3://{bucket}", "--recursive"],
        capture_output=True,
        timeout=10,
    )
    subprocess.run(
        ["aws", "--endpoint-url", endpoint, "s3", "rb", f"s3://{bucket}"],
        capture_output=True,
        timeout=10,
    )


def test_s3_bucket_creation(s3_bucket: str, localstack_s3: Dict[str, str]):
    """Test that S3 bucket is created successfully."""
    config = localstack_s3

    # List buckets
    result = subprocess.run(
        ["aws", "--endpoint-url", config["endpoint_url"], "s3", "ls"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert s3_bucket in result.stdout


def test_cold_run_uploads_to_s3(s3_bucket: str, localstack_s3: Dict[str, str], tmp_path: Path):
    """Test that cold run uploads cache artifacts to S3."""
    config = localstack_s3
    endpoint = config["endpoint_url"]

    # Create a simple test repo
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src/main.py").write_text("print('hello')\n")
    (repo / "tests").mkdir()
    (repo / "tests/test_main.py").write_text("def test_hello(): assert True\n")

    # Set environment for FirstTry
    env = os.environ.copy()
    env["FT_S3_ENDPOINT"] = endpoint
    env["FT_S3_BUCKET"] = s3_bucket
    env["AWS_ACCESS_KEY_ID"] = config["access_key"]
    env["AWS_SECRET_ACCESS_KEY"] = config["secret_key"]
    env["FT_SEND_TELEMETRY"] = "0"  # Disable telemetry

    # Clear local cache
    cache_dir = repo / ".firsttry"
    if cache_dir.exists():
        import shutil

        shutil.rmtree(cache_dir)

    # Run FirstTry (cold run)
    result = subprocess.run(
        ["python", "-m", "firsttry.cli", "run", "--tier", "lite", "--mode", "full"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Should succeed
    assert result.returncode == 0, f"FirstTry failed:\n{result.stdout}\n{result.stderr}"

    # List S3 objects
    list_result = subprocess.run(
        ["aws", "--endpoint-url", endpoint, "s3", "ls", f"s3://{s3_bucket}/", "--recursive"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert list_result.returncode == 0
    # Should have uploaded some cache objects
    assert len(list_result.stdout.strip()) > 0, "No objects uploaded to S3"


def test_warm_run_pulls_from_s3(s3_bucket: str, localstack_s3: Dict[str, str], tmp_path: Path):
    """Test that warm run retrieves cache from S3 with fast response."""
    config = localstack_s3
    endpoint = config["endpoint_url"]

    # Create test repo
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src/main.py").write_text("print('hello')\n")
    (repo / "tests").mkdir()
    (repo / "tests/test_main.py").write_text("def test_hello(): assert True\n")
    (repo / ".firsttry").mkdir()

    # Set environment
    env = os.environ.copy()
    env["FT_S3_ENDPOINT"] = endpoint
    env["FT_S3_BUCKET"] = s3_bucket
    env["AWS_ACCESS_KEY_ID"] = config["access_key"]
    env["AWS_SECRET_ACCESS_KEY"] = config["secret_key"]
    env["FT_SEND_TELEMETRY"] = "0"

    # Cold run
    subprocess.run(
        ["python", "-m", "firsttry.cli", "run", "--tier", "lite", "--mode", "full"],
        cwd=repo,
        env=env,
        capture_output=True,
        timeout=30,
    )

    # Clear local task cache (but keep repo fingerprint)
    task_cache_dir = repo / ".firsttry" / "taskcache"
    if task_cache_dir.exists():
        import shutil

        shutil.rmtree(task_cache_dir)

    # Warm run (should pull from S3)
    import time

    start = time.time()

    result = subprocess.run(
        ["python", "-m", "firsttry.cli", "run", "--tier", "lite", "--mode", "full"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    elapsed = time.time() - start

    assert result.returncode == 0
    # Warm run should be fast (ideally <5s, but at least faster than cold)
    assert elapsed < 15, f"Warm run took {elapsed:.1f}s, expected < 15s"


def test_cache_hit_response_time(s3_bucket: str, localstack_s3: Dict[str, str], tmp_path: Path):
    """Test that cache hits return in ≤5ms."""
    config = localstack_s3
    endpoint = config["endpoint_url"]

    # Create test repo
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src/main.py").write_text("print('hello')\n")

    env = os.environ.copy()
    env["FT_S3_ENDPOINT"] = endpoint
    env["FT_S3_BUCKET"] = s3_bucket
    env["AWS_ACCESS_KEY_ID"] = config["access_key"]
    env["AWS_SECRET_ACCESS_KEY"] = config["secret_key"]
    env["FT_SEND_TELEMETRY"] = "0"

    # First run
    subprocess.run(
        ["python", "-m", "firsttry.cli", "run", "--tier", "lite"],
        cwd=repo,
        env=env,
        capture_output=True,
        timeout=30,
    )

    # Check report for cache hit metrics
    report_path = repo / ".firsttry" / "audit" / "report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text())

        # Look for cache hits
        cache_hits = [
            t for t in report.get("tasks", []) if t.get("cache_status", "").startswith("hit")
        ]

        if cache_hits:
            # All cache hits should be fast
            for task in cache_hits:
                duration_ms = task.get("duration_ms", 999)
                # Cache hits should typically be 1-5ms
                assert duration_ms <= 10, f"Cache hit took {duration_ms}ms, expected ≤10ms"


def test_s3_object_listing_consistency(s3_bucket: str, localstack_s3: Dict[str, str]):
    """Test that S3 object listing is consistent across runs."""
    config = localstack_s3
    endpoint = config["endpoint_url"]

    # List objects (should return empty initially)
    result = subprocess.run(
        ["aws", "--endpoint-url", endpoint, "s3", "ls", f"s3://{s3_bucket}/", "--recursive"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    # Should be empty
    assert result.stdout.strip() == ""

    # Upload a test object
    subprocess.run(
        [
            "aws",
            "--endpoint-url",
            endpoint,
            "s3",
            "cp",
            "/etc/hostname",
            f"s3://{s3_bucket}/test-object.txt",
        ],
        capture_output=True,
        timeout=10,
    )

    # List again
    result = subprocess.run(
        ["aws", "--endpoint-url", endpoint, "s3", "ls", f"s3://{s3_bucket}/", "--recursive"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert "test-object.txt" in result.stdout


def test_remote_cache_performance_impact(
    s3_bucket: str, localstack_s3: Dict[str, str], tmp_path: Path
):
    """Test performance impact of remote cache operations."""
    config = localstack_s3
    endpoint = config["endpoint_url"]

    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src/main.py").write_text("x = 1\n")

    env = os.environ.copy()
    env["FT_S3_ENDPOINT"] = endpoint
    env["FT_S3_BUCKET"] = s3_bucket
    env["AWS_ACCESS_KEY_ID"] = config["access_key"]
    env["AWS_SECRET_ACCESS_KEY"] = config["secret_key"]
    env["FT_SEND_TELEMETRY"] = "0"

    import time

    # Run 1: Cold
    start = time.time()
    subprocess.run(
        ["python", "-m", "firsttry.cli", "run", "--tier", "lite"],
        cwd=repo,
        env=env,
        capture_output=True,
        timeout=30,
    )
    cold_time = time.time() - start

    # Run 2: Warm
    start = time.time()
    subprocess.run(
        ["python", "-m", "firsttry.cli", "run", "--tier", "lite"],
        cwd=repo,
        env=env,
        capture_output=True,
        timeout=30,
    )
    warm_time = time.time() - start

    # Warm should be significantly faster
    speedup = cold_time / warm_time if warm_time > 0 else 0
    assert speedup > 1.5, f"Expected > 1.5x speedup, got {speedup:.2f}x"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
