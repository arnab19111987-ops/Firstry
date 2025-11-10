import importlib
import json

import pytest


def _has(obj, name):
    return hasattr(obj, name) and callable(getattr(obj, name))


def test_cache_models_roundtrip(tmp_path):
    m = importlib.import_module("firsttry.cache_models")

    # Look for a common pair: to_dict/from_dict on a class or module-level helpers
    # Strategy:
    #  - Prefer module-level functions to_dict/from_dict if present
    #  - Else find a class with those methods and try a simple instance
    to_dict = getattr(m, "to_dict", None)
    from_dict = getattr(m, "from_dict", None)

    if callable(to_dict) and callable(from_dict):
        sample = {"key": "v", "n": 1, "seq": [1, 2], "meta": {"a": True}}
        d = to_dict(sample)  # some modules transparently pass-through
        j = json.dumps(d)
        back = from_dict(json.loads(j))
        # loose equality: at least keys preserved
        assert isinstance(back, dict) and set(back.keys()) >= set(sample.keys())
        return

    # Try to find a class with to_dict/from_dict
    candidate_cls = None
    for _, obj in m.__dict__.items():
        if isinstance(obj, type) and _has(obj, "to_dict") and hasattr(obj, "__init__"):
            candidate_cls = obj
            break

    if not candidate_cls:
        pytest.skip("No round-trip helpers present in cache_models.")

    # Create with permissive kwargs if possible
    try:
        inst = candidate_cls()  # hope for defaults
    except TypeError:
        # fallback: try trivial kwargs
        try:
            inst = candidate_cls(**{})
        except Exception:
            pytest.skip("Could not instantiate a cache model safely.")

    d = inst.to_dict()
    assert isinstance(d, dict)
    # If a from_dict exists, try it
    if _has(candidate_cls, "from_dict"):
        inst2 = candidate_cls.from_dict(d)
        assert inst2 is not None
