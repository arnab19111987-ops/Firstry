#!/usr/bin/env bash
# Local CI helper for the repository. Designed to be idempotent and resilient.
# Usage:
#   AUTOFIX=1 bash local_ci.sh    # run with autofix for ruff
#   bash local_ci.sh              # run checks without autofix

set -u
FAIL=0
AUTOFIX=${AUTOFIX:-0}

echo "Local CI starting (AUTOFIX=${AUTOFIX})"

run_cmd() {
  echo "\n>>> $*"
  if ! "$@"; then
    echo "[FAIL] command failed: $*"
    FAIL=1
  fi
}

# Try to ensure the editable packages and dev tools are available. These are no-ops
# if already installed.
echo "Ensuring Python packages (editable installs + dev tools). This may take a moment."
python -m pip install -e tools/firsttry -e licensing >/dev/null 2>&1 || true
python -m pip install ruff black mypy pytest types-PyYAML types-click >/dev/null 2>&1 || true

# Lint / format / typecheck
if command -v ruff >/dev/null 2>&1; then
  if [ "${AUTOFIX}" = "1" ]; then
    run_cmd ruff check --fix . || true
  else
    run_cmd ruff check . || true
  fi
else
  echo "ruff not installed; skip ruff checks"
  FAIL=1
fi

if command -v black >/dev/null 2>&1; then
  run_cmd black . || true
else
  echo "black not installed; skip formatting"
  FAIL=1
fi

if command -v mypy >/dev/null 2>&1; then
  run_cmd mypy . || true
else
  echo "mypy not installed; skip type checking"
  FAIL=1
fi

# Run python tests (point PYTHONPATH at licensing so the tests import correctly)
echo "Running Python tests"
if ! PYTHONPATH=licensing pytest -q; then
  echo "Python tests failed"
  FAIL=1
fi

# Run the node validator (scripts/validate-node.sh) which runs npm installs, lint, typecheck, tests
echo "Running node validator"
if ! bash scripts/validate-node.sh; then
  echo "Node validation failed"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "\n✓ local_ci: all checks passed"
  exit 0
else
  echo "\n✗ local_ci: some checks failed (see output above)"
  exit 2
fi
