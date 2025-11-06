from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class CacheHit:
    # subprocess outputs may be str or bytes depending on how callers invoke
    # subprocess.run (text=True vs bytes). Accept both to reduce friction.
    stdout: str | bytes = ""
    stderr: str | bytes = ""
    meta: Dict[str, Any] | None = None  # freeform (e.g., tool versions, timings)


class BaseCache(ABC):
    """Abstract cache interface."""

    @abstractmethod
    def get(self, key: str) -> Optional[CacheHit]:
        raise NotImplementedError

    @abstractmethod
    def put(self, key: str, result: CacheHit) -> None:
        raise NotImplementedError
