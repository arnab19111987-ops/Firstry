#!/usr/bin/env bash
# Ultra-fast dev routine - single-command alternative to Makefile
# Deterministic + no-hang defaults for CI/local development
set -euo pipefail

# Export deterministic defaults
export PYTHONHASHSEED=0
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export FT_SKIP_TOOL_EXEC=1

# Helper: run with timeout
run() {
  name="$1"; shift
  echo ">>> $name"
  timeout --preserve-status -k 5s 120s bash -lc "$@"
}

# Helper: conditionally run tool (skip if not installed)
maybe() {
  tool="$1"; shift
  if command -v "$tool" >/dev/null 2>&1; then 
    run "$tool $*" "$tool $*"
  else 
    echo "SKIP ($tool not found)"
  fi
}

echo "=== Fast Dev Routine (deterministic + no-hang) ==="

# 1. Smoke tests
run "smoke tests" "pytest -q -k 'import or smoke' --maxfail=1 --no-header --no-summary || true"

# 2. CLI ping
timeout --preserve-status -k 5s 20s python -m firsttry --help >/dev/null 2>&1 || \
  timeout --preserve-status -k 5s 20s firsttry --help >/dev/null 2>&1 || \
  echo "SKIP (CLI not available)"

# 3. Fast tests
run "fast tests" "pytest -q -k 'not slow' --maxfail=1 --no-header --no-summary"

# 4. Parallel checks (linting + type-checking)
echo ">>> parallel checks"
( maybe ruff "check ." ) &
( maybe black "--check ." ) &
( maybe isort "--check-only ." ) &
( maybe mypy "src" ) &
wait

# 5. Coverage slice (non-blocking)
echo ">>> coverage (non-blocking)"
timeout --preserve-status -k 5s 120s pytest -q --maxfail=1 --no-header --no-summary \
  --cov=src/firsttry --cov-branch --cov-report=term-missing || true

echo "✅ All dev routines complete (fast, timed, reliable)"
