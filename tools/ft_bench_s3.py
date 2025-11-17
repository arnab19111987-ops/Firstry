"""S3/R2 storage integration for benchmark harness artifact archival.

Provides secure, configurable artifact upload with environment variable support.
No external dependencies - uses boto3 (optional) with graceful fallback.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Optional boto3 dependency
try:
    import boto3

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


@dataclass
class S3Config:
    """S3/R2 configuration from environment variables."""

    access_key_id: str
    secret_access_key: str
    endpoint_url: str
    bucket_name: str
    region: str = "auto"
    prefix: str = "benchmarks"
    enabled: bool = True

    @classmethod
    def from_env(cls) -> S3Config | None:
        """Load configuration from environment variables.

        Expected variables:
        - S3_ACCESS_KEY_ID or AWS_ACCESS_KEY_ID
        - S3_SECRET_ACCESS_KEY or AWS_SECRET_ACCESS_KEY
        - S3_ENDPOINT_URL
        - S3_BUCKET_NAME
        - S3_REGION (optional, default: "auto")
        - S3_PREFIX (optional, default: "benchmarks")
        - S3_ENABLED (optional, default: "true")
        """
        # Check if S3 is disabled
        enabled = os.getenv("S3_ENABLED", "true").lower() in {"true", "1", "yes"}
        if not enabled:
            return None

        # Get credentials (support both S3_* and AWS_* prefixes)
        access_key_id = os.getenv("S3_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
        secret_access_key = os.getenv("S3_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
        endpoint_url = os.getenv("S3_ENDPOINT_URL")
        bucket_name = os.getenv("S3_BUCKET_NAME")

        # All required fields must be set
        if not all([access_key_id, secret_access_key, endpoint_url, bucket_name]):
            return None

        return cls(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            endpoint_url=endpoint_url,
            bucket_name=bucket_name,
            region=os.getenv("S3_REGION", "auto"),
            prefix=os.getenv("S3_PREFIX", "benchmarks"),
            enabled=enabled,
        )

    def to_dict(self) -> dict[str, str]:
        """Return config as dict (without secrets for logging)."""
        return {
            "endpoint_url": self.endpoint_url,
            "bucket_name": self.bucket_name,
            "region": self.region,
            "prefix": self.prefix,
        }


@dataclass
class S3UploadResult:
    """Result of S3 upload operation."""

    success: bool
    url: str | None = None
    key: str | None = None
    error: str | None = None
    size_bytes: int | None = None
    upload_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class S3ArchiveManager:
    """Manages benchmark artifact archival to S3/R2."""

    def __init__(self, config: S3Config | None = None):
        """Initialize with optional config. If None, will try to load from env."""
        self.config = config or S3Config.from_env()
        self.client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize boto3 S3 client if available and configured."""
        if not self.config or not BOTO3_AVAILABLE:
            return

        try:
            self.client = boto3.client(
                "s3",
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                endpoint_url=self.config.endpoint_url,
                region_name=self.config.region,
            )
            # Test connection with head_bucket
            self.client.head_bucket(Bucket=self.config.bucket_name)
        except Exception as e:
            self.client = None
            print(f"[WARN] S3 connection failed: {e}", file=sys.stderr)

    def is_available(self) -> bool:
        """Check if S3 archival is available and configured."""
        return self.client is not None and self.config is not None

    def _compute_object_key(
        self,
        repo_root: str,
        run_type: str,
        timestamp: str | None = None,
    ) -> str:
        """Compute S3 object key for benchmark artifact.

        Format: {prefix}/{repo_hash}/{timestamp}-{run_type}.json
        """
        if not timestamp:
            timestamp = datetime.utcnow().isoformat() + "Z"

        # Compute short repo identifier (first 8 chars of content hash)
        repo_hash = self._compute_repo_id(repo_root)

        return f"{self.config.prefix}/{repo_hash}/{timestamp}-{run_type}.json"

    def _compute_repo_id(self, repo_root: str) -> str:
        """Compute short identifier for repository."""
        hasher = hashlib.sha256()

        # Hash repo name and path
        repo_name = Path(repo_root).name
        hasher.update(repo_name.encode())
        hasher.update(repo_root.encode())

        return hasher.hexdigest()[:8]

    def upload_benchmark_report(
        self,
        report_data: dict[str, Any],
        repo_root: str,
        run_type: str = "benchmark",
    ) -> S3UploadResult:
        """Upload benchmark report to S3.

        Args:
            report_data: Benchmark report data (typically from JSON file)
            repo_root: Repository root path
            run_type: Type of run (e.g., "benchmark", "regression-check")

        Returns:
            S3UploadResult with status and URL
        """
        if not self.is_available():
            return S3UploadResult(
                success=False,
                error="S3 not available or not configured",
            )

        try:
            import time

            start_time = time.time()

            # Prepare upload
            key = self._compute_object_key(repo_root, run_type)
            body = json.dumps(report_data, indent=2)
            size_bytes = len(body.encode())

            # Upload to S3
            self.client.put_object(
                Bucket=self.config.bucket_name,
                Key=key,
                Body=body,
                ContentType="application/json",
                Metadata={
                    "repo": Path(repo_root).name,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            upload_time_ms = (time.time() - start_time) * 1000

            # Construct URL
            url = f"{self.config.endpoint_url.rstrip('/')}/{self.config.bucket_name}/{key}"

            return S3UploadResult(
                success=True,
                url=url,
                key=key,
                size_bytes=size_bytes,
                upload_time_ms=upload_time_ms,
            )

        except Exception as e:
            return S3UploadResult(
                success=False,
                error=f"Upload failed: {e}",
            )

    def upload_from_file(
        self,
        local_path: str | Path,
        repo_root: str,
        run_type: str = "benchmark",
    ) -> S3UploadResult:
        """Upload benchmark report from local file.

        Args:
            local_path: Path to JSON report file
            repo_root: Repository root path
            run_type: Type of run

        Returns:
            S3UploadResult with status and URL
        """
        local_path = Path(local_path)

        if not local_path.exists():
            return S3UploadResult(
                success=False,
                error=f"File not found: {local_path}",
            )

        try:
            data = json.loads(local_path.read_text())
            return self.upload_benchmark_report(data, repo_root, run_type)
        except Exception as e:
            return S3UploadResult(
                success=False,
                error=f"Failed to read/upload file: {e}",
            )

    def list_reports(self, repo_root: str, max_keys: int = 100) -> list[str]:
        """List benchmark reports for a repository.

        Args:
            repo_root: Repository root path
            max_keys: Maximum number of keys to return

        Returns:
            List of object keys
        """
        if not self.is_available():
            return []

        try:
            repo_id = self._compute_repo_id(repo_root)
            prefix = f"{self.config.prefix}/{repo_id}/"

            response = self.client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys,
            )

            return [obj["Key"] for obj in response.get("Contents", [])]
        except Exception:
            return []

    def download_report(
        self,
        key: str,
    ) -> dict[str, Any] | None:
        """Download and parse benchmark report from S3.

        Args:
            key: S3 object key

        Returns:
            Parsed report data or None on error
        """
        if not self.is_available():
            return None

        try:
            response = self.client.get_object(
                Bucket=self.config.bucket_name,
                Key=key,
            )
            data = json.loads(response["Body"].read().decode())
            return data
        except Exception:
            return None

    def generate_report_url(self, key: str) -> str | None:
        """Generate a presigned URL for a report (if supported).

        Args:
            key: S3 object key

        Returns:
            Presigned URL or None if not available
        """
        if not self.is_available():
            return None

        try:
            # For R2, we can generate a public URL directly
            url = f"{self.config.endpoint_url.rstrip('/')}/{self.config.bucket_name}/{key}"
            return url
        except Exception:
            return None


def main():
    """Demo: Test S3 integration."""
    config = S3Config.from_env()

    if not config:
        print("S3 configuration not found in environment variables")
        print("\nRequired environment variables:")
        print("  S3_ACCESS_KEY_ID")
        print("  S3_SECRET_ACCESS_KEY")
        print("  S3_ENDPOINT_URL")
        print("  S3_BUCKET_NAME")
        print("\nOptional:")
        print("  S3_REGION (default: 'auto')")
        print("  S3_PREFIX (default: 'benchmarks')")
        print("  S3_ENABLED (default: 'true')")
        return 1

    print("S3 Configuration:")
    print(json.dumps(config.to_dict(), indent=2))

    manager = S3ArchiveManager(config)

    if not manager.is_available():
        print("\n[ERROR] S3 manager not available (boto3 not installed?)")
        return 1

    print("\n✓ S3 connection successful")

    # Demo: List reports
    reports = manager.list_reports("/workspaces/Firstry", max_keys=5)
    print(f"\nRecent reports ({len(reports)} found):")
    for key in reports[:5]:
        print(f"  - {key}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
