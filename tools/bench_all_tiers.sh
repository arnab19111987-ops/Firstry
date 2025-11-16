#!/usr/bin/env bash
set -euo pipefail

echo "This script has moved to tools/internal/bench_all_tiers_internal.sh"
echo "If you intended to run the heavy internal harness, run:" 
echo "  bash tools/internal/bench_all_tiers_internal.sh"
echo "This top-level script is intentionally a lightweight wrapper to avoid
accidentally running heavy experiments in user environments."
