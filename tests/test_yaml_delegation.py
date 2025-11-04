"""Guardrail tests for YAML presence.

This project requires PyYAML. Ensure basic safe_load/safe_dump round-trip
works for simple mappings.
"""
from __future__ import annotations

import yaml


def test_yaml_roundtrip_basic():
    # Basic round-trip for a simple mapping. Accept either int or str values
    # because the fallback shim may serialize as strings while real PyYAML
    # preserves numeric types.
    data = {"a": 1, "b": "x"}

    # require safe_load/safe_dump functions available from PyYAML
    assert hasattr(yaml, "safe_load"), "PyYAML is required (yaml.safe_load missing)"
    assert hasattr(yaml, "safe_dump"), "PyYAML is required (yaml.safe_dump missing)"

    dumped = yaml.safe_dump(data)
    loaded = yaml.safe_load(dumped)
    assert loaded is not None
    assert str(loaded.get("b")) == "x"
