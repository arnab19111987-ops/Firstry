#!/usr/bin/env bash
set -euo pipefail

echo "Running firsttry parity self-check (fast)"
python -m firsttry.ci_parity.parity_runner --self-check --quiet || true

echo
echo "Running demo pre-commit fast gate (will scan for secrets)"
python -c "from firsttry.cli import pre_commit_fast_gate; import sys; sys.exit(pre_commit_fast_gate())"

echo
echo "If the secret scanner flagged files, it returns exit code 97."
