from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from .base import BaseCache
from .base import CacheHit


def _has_boto3() -> bool:
    try:
        import boto3  # noqa: F401

        return True
    except Exception:
        return False


@dataclass
class _S3Conf:
    bucket: str
    prefix: str  # key prefix without trailing slash


class S3Cache(BaseCache):
    def __init__(self, conf: _S3Conf):
        self.conf = conf
        self.enabled = _has_boto3()
        if self.enabled:
            import boto3

            self.s3 = boto3.client("s3")
        else:
            self.s3 = None

    @staticmethod
    def from_env() -> S3Cache | None:
        b = os.getenv("FT_S3_BUCKET")
        p = os.getenv("FT_S3_PREFIX", "").rstrip("/")
        if not b or not p:
            return None
        return S3Cache(_S3Conf(bucket=b, prefix=p))

    def _key(self, key: str) -> str:
        return f"{self.conf.prefix}/{key}.json"

    def get(self, key: str) -> CacheHit | None:
        if not self.enabled or not self.s3:
            return None
        try:
            obj = self.s3.get_object(Bucket=self.conf.bucket, Key=self._key(key))
            data = json.loads(obj["Body"].read().decode("utf-8"))
            return CacheHit(
                stdout=data.get("stdout", ""),
                stderr=data.get("stderr", ""),
                meta=data.get("meta"),
            )
        except Exception:
            return None

    def put(self, key: str, result: CacheHit) -> None:
        if not self.enabled or not self.s3:
            return
        try:
            payload: dict[str, Any] = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "meta": result.meta or {},
            }
            self.s3.put_object(
                Bucket=self.conf.bucket,
                Key=self._key(key),
                Body=json.dumps(payload).encode("utf-8"),
                ContentType="application/json",
                CacheControl="max-age=31536000,immutable",
            )
        except Exception:
            # fail-closed: cache is an optimization
            return
