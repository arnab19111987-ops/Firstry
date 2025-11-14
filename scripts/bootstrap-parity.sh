#!/usr/bin/env bash
set -Eeuo pipefail
PY=${PY:-python3}
$PY -m venv .venv-parity
. .venv-parity/bin/activate
pip install --upgrade pip wheel jq || true
jq -r '.pip[]' .firsttry/parity.lock.json | xargs -n1 -I{} pip install "{}" || true
pip install -e . || true
echo "[ft] parity ready"
