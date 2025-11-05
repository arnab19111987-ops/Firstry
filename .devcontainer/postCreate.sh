#!/usr/bin/env bash
set -u  # no -e here; we don't want a single failure to kill the container
LOG=/tmp/postCreate.log
{
  echo "=== postCreate $(date -Iseconds) ==="
  echo "uname -a: $(uname -a)"
  echo "whoami: $(whoami)"

  # Example: safe apt operations
  sudo bash -lc 'apt-get update -y || true'
  sudo bash -lc 'apt-get install -y --no-install-recommends git jq >/dev/null 2>&1 || true'

  # Example: Python deps (make these best-effort)
  if [ -f requirements.txt ]; then
    python -m pip install -U pip || true
    pip install -r requirements.txt || true
  fi

  echo "postCreate completed."
} >>"$LOG" 2>&1
