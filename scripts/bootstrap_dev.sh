#!/usr/bin/env bash
set -euo pipefail

python -m pip install -e .
python -m pip install -r requirements.txt || true
python -m pip install -r requirements-dev.txt 2>/dev/null || true
command -v ruff >/dev/null || python -m pip install ruff
command -v mypy >/dev/null || python -m pip install mypy
command -v pytest >/dev/null || python -m pip install pytest

echo "✅ Dev bootstrap complete. Try: ft --help || python -m firsttry --help"
