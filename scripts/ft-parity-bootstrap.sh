#!/usr/bin/env bash
# FirstTry CI Parity Bootstrap Script
# Ensures hermetic, reproducible environment for local CI parity runs

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[PARITY] Starting bootstrap in $ROOT"

# Create fresh venv
if [ -d ".venv-parity" ]; then
    echo "[PARITY] Removing existing .venv-parity"
    rm -rf .venv-parity
fi

python3 -m venv .venv-parity
source .venv-parity/bin/activate

echo "[PARITY] Installing base packages"
python -m pip install --upgrade pip wheel setuptools --quiet

echo "[PARITY] Installing package and dev requirements"
pip install -e . --quiet
pip install -r requirements-dev.txt --quiet

# Verify required plugins
echo "[PARITY] Verifying required plugins"
python - <<'PY'
import importlib
import sys

# Map package names to import names
plugin_map = {
    "pytest-cov": "pytest_cov",
    "pytest-timeout": "pytest_timeout",
    "pytest-xdist": "xdist",
    "pytest-rerunfailures": "pytest_rerunfailures"
}
missing = []

for pkg_name, import_name in plugin_map.items():
    try:
        importlib.import_module(import_name)
        print(f"  ✓ {pkg_name}")
    except ImportError as e:
        print(f"  ✗ {pkg_name}: {e}")
        missing.append(pkg_name)

if missing:
    print(f"\n[PARITY] ERROR: Missing plugins: {', '.join(missing)}")
    sys.exit(2)

print("[PARITY] All plugins OK")
PY

# Clean caches (prevents stale greens)
echo "[PARITY] Cleaning caches"
rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage artifacts || true
mkdir -p artifacts

# Set deterministic environment variables
echo "[PARITY] Setting deterministic environment"
export CI=true
export TZ=UTC
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0

# Save env to a file for later sourcing
cat > .venv-parity/parity-env.sh <<'EOF'
export CI=true
export TZ=UTC
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0
EOF

echo "[PARITY] Bootstrap complete"
echo "[PARITY] To activate: source .venv-parity/bin/activate"
echo "[PARITY] Environment vars: source .venv-parity/parity-env.sh"
