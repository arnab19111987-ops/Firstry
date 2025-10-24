from __future__ import annotations
import os
from typing import Dict, List

# Simple in-memory “DB” loaded from env for demo:
# FIRSTTRY_KEYS="ABC123,PRO456:featA|featB,TRIAL789:trial"
#   - plain key => default features []
#   - key:feat1|feat2 => explicit features


def _parse_feature_blob(blob: str) -> List[str]:
    return [f for f in blob.split("|") if f]


def load_key_store() -> Dict[str, List[str]]:
    raw = os.getenv("FIRSTTRY_KEYS", "").strip()
    store: Dict[str, List[str]] = {}
    if not raw:
        return store
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            k, feats = token.split(":", 1)
            store[k] = _parse_feature_blob(feats)
        else:
            store[token] = []
    return store


KEYS = load_key_store()


def verify(product: str, key: str):
    if product != "firsttry":
        return False, "unknown product", []
    if key in KEYS:
        return True, None, KEYS[key]
    return False, "key not found", []
