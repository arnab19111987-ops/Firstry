#!/usr/bin/env bash
set -euo pipefail

# Lightweight warm-up to reduce first-run latency
echo "[postStart] Warming caches..."
python - <<'PY'
try:
    import sys, importlib, json
    importlib.invalidate_caches()
    print("[py] Interpreter:", sys.version.split()[0])
except Exception as e:
    print("[py] Warmup failed:", e)
PY

# Optional: create tool caches so they don't thrash the FS
mkdir -p .firsttry .mypy_cache .pytest_cache .ruff_cache || true

echo "[postStart] Ready."
