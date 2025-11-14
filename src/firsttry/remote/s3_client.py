from __future__ import annotations

import os
import random
import time
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Optional


class S3PolicyError(RuntimeError): ...


def retry_jitter(fn: Callable[[], Any], attempts=5, base=0.2, cap=5.0):
    for i in range(attempts):
        try:
            return fn()
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(min(cap, base * (2**i) + random.random() * base))


def _client(region: Optional[str]):
    import boto3

    return boto3.client("s3", region_name=region or os.getenv("AWS_REGION"))


def ensure_bucket_policy(cfg) -> None:
    b = cfg.remote.s3_bucket
    if not b:
        return
    if cfg.remote.allow_buckets and b not in set(cfg.remote.allow_buckets):
        raise S3PolicyError(f"Bucket {b} not in allow-list")


def ensure_kms_enabled(cfg) -> None:
    if not cfg.remote.require_kms:
        return
    # Soft-validate at runtime
    try:
        s3 = _client(cfg.remote.region)
        info = s3.get_bucket_encryption(Bucket=cfg.remote.s3_bucket)
        rules = info.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
        if not any(
            r.get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm") == "aws:kms"
            for r in rules
        ):
            raise S3PolicyError("S3 bucket missing SSE-KMS default encryption")
    except Exception as e:
        raise S3PolicyError(f"KMS validation failed: {e}")


def upload_file(cfg, local: Path, key: str):
    ensure_bucket_policy(cfg)
    ensure_kms_enabled(cfg)
    s3 = _client(cfg.remote.region)
    extra = {}
    if cfg.remote.require_kms:
        extra["ServerSideEncryption"] = "aws:kms"

    def op():
        s3.upload_file(str(local), cfg.remote.s3_bucket, key, ExtraArgs=extra or None)

    retry_jitter(op)


def download_file(cfg, key: str, dest: Path):
    s3 = _client(cfg.remote.region)

    def op():
        s3.download_file(cfg.remote.s3_bucket, key, str(dest))

    retry_jitter(op)
