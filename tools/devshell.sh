#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
if [ ! -d .venv ]; then
  python -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -U pip setuptools wheel >/dev/null
pip install -e . >/dev/null
echo "Ready → $(python -V), ft=$(which ft || echo MISSING)"
exec "$SHELL" -l
