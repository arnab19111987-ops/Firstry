"""Fast JSON I/O with orjson fallback to stdlib json.

Provides drop-in replacements for json.dumps/loads that prefer orjson
(C-accelerated binary JSON) but gracefully fallback to stdlib json if
orjson is not available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Try to import orjson; fall back to json
try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    import json

    HAS_ORJSON = False


def dumps(obj: Any, *, default: Any = None, **kw: Any) -> str:
    """Serialize obj to JSON string (fast with orjson or fallback).

    Args:
        obj: Object to serialize
        default: Callable for objects that can't be serialized
        **kw: Additional keyword arguments (passed to json.dumps if orjson unavailable)

    Returns:
        JSON string
    """
    if HAS_ORJSON:
        # orjson.dumps returns bytes; decode to str
        return orjson.dumps(obj, default=default).decode("utf-8")
    else:
        # Fall back to stdlib json
        return json.dumps(obj, default=default, separators=(",", ":"), **kw)


def loads(s: str | bytes) -> Any:
    """Deserialize JSON string/bytes to Python object.

    Args:
        s: JSON string or bytes

    Returns:
        Deserialized Python object
    """
    if HAS_ORJSON:
        return orjson.loads(s)
    else:
        if isinstance(s, bytes):
            s = s.decode("utf-8")
        return json.loads(s)


def write_report(obj: Any, path: str | "Path") -> None:
    """Write JSON report to path using fast serializer.

    Args:
        obj: Python object to serialize
        path: Destination path to write
    """
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(dumps(obj), encoding="utf-8")
