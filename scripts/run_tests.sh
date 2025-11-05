#!/usr/bin/env bash
set -euo pipefail

# Runs the repo tests in two isolated pytest invocations to avoid test-package
# module-name collisions between top-level `tests/` and `licensing/tests/`.

export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

echo "Running top-level tests/..."
./.venv/bin/pytest -q tests || { echo "Top-level tests failed"; exit 1; }

echo "Running licensing tests/..."
./.venv/bin/pytest -q licensing/tests || { echo "Licensing tests failed"; exit 1; }

echo "All tests passed (both subsets)."
