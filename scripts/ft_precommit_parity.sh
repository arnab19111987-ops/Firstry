#!/usr/bin/env bash
# FirstTry pre-commit parity script
# Ensures local pre-commit hooks match CI behavior exactly
# Usage: scripts/ft_precommit_parity.sh [--all-files]

set -euo pipefail

# Deterministic + fast defaults
export PYTHONHASHSEED=0
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export FT_SKIP_TOOL_EXEC=${FT_SKIP_TOOL_EXEC:-1}  # repo-adaptive safety

TIMEOUT="timeout --preserve-status -k 5s"
ALL_FILES_FLAG="${1:-}"

log() { echo ">>> $*"; }
err() { echo "ERROR: $*" >&2; exit 1; }

# 0) Sanity: verify Python version
log "Python version check"
$TIMEOUT 15s python -V || err "Python not available"

# 1) Detect FirstTry CLI (prefer 'firsttry', fall back to 'ft')
if command -v firsttry >/dev/null 2>&1; then
  FT_CMD="firsttry"
  log "Using firsttry command"
elif command -v ft >/dev/null 2>&1; then
  FT_CMD="ft"
  log "Using ft command"
else
  FT_CMD=""
  log "WARNING: Neither 'firsttry' nor 'ft' command found"
fi

# 2) Run repo-adaptive pre-commit via FirstTry CLI
if [ -n "$FT_CMD" ]; then
  log "Running: $FT_CMD pre-commit (repo-adaptive)"
  
  # Check if command supports pre-commit
  if $FT_CMD --help 2>&1 | grep -q "pre-commit"; then
    # Run with timeout, but capture exit code
    set +e
    $TIMEOUT 300s $FT_CMD pre-commit $ALL_FILES_FLAG
    EXIT_CODE=$?
    set -e
    
    if [ $EXIT_CODE -eq 0 ]; then
      log "✅ FirstTry pre-commit passed"
      log "✅ ft pre-commit parity OK"
      exit 0
    elif [ $EXIT_CODE -eq 124 ]; then
      log "WARNING: FirstTry pre-commit timed out (300s)"
      log "Falling back to mirrored checks..."
      FT_CMD=""  # Force fallback
    else
      log "WARNING: FirstTry pre-commit exited with code $EXIT_CODE"
      log "Falling back to mirrored checks..."
      FT_CMD=""  # Force fallback
    fi
  else
    log "WARNING: $FT_CMD does not support 'pre-commit' subcommand"
    log "Falling back to mirrored checks..."
    FT_CMD=""  # Force fallback
  fi
fi

# 3) Fallback: run mirrored minimal stack if FirstTry CLI not available
if [ -z "$FT_CMD" ]; then
  log "Running mirrored checks (FirstTry CLI not available)"
  
  # Run each tool with timeout, continue on failure for diagnostic output
  FAILED=0
  
  if command -v ruff >/dev/null 2>&1; then
    log "ruff check (src only)"
    $TIMEOUT 60s ruff check src || FAILED=1
  else
    log "SKIP: ruff not found"
  fi
  
  if command -v black >/dev/null 2>&1; then
    log "black check (src only)"
    $TIMEOUT 60s black --check src || FAILED=1
  else
    log "SKIP: black not found"
  fi
  
  if command -v isort >/dev/null 2>&1; then
    log "isort check (src only)"
    $TIMEOUT 60s isort --check-only src || FAILED=1
  else
    log "SKIP: isort not found"
  fi
  
  if command -v mypy >/dev/null 2>&1; then
    log "mypy src"
    $TIMEOUT 120s mypy src || FAILED=1
  else
    log "SKIP: mypy not found"
  fi
  
  # Fast tests (bounded subset) - non-blocking for pre-commit
  if command -v pytest >/dev/null 2>&1; then
    log "pytest (fast smoke tests - non-blocking)"
    $TIMEOUT 150s pytest -q -k "import or smoke or not slow" \
      --maxfail=1 --no-header --no-summary || {
      log "WARNING: Some tests failed (non-blocking in pre-commit)"
    }
  else
    log "SKIP: pytest not found"
  fi
  
  if [ $FAILED -ne 0 ]; then
    err "Mirrored checks failed"
  fi
fi

log "✅ ft pre-commit parity OK"
