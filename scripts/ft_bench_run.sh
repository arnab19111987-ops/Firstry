#!/bin/bash
# FirstTry Benchmark Harness Shell Wrapper
#
# Usage: ft_bench_run.sh [OPTIONS]
#   --tier lite|pro          FirstTry tier (default: lite)
#   --mode fast|full         FirstTry mode (default: fast)
#   --max-procs N            Max parallel processes (default: auto)
#   --timeout-s S            Timeout per run (default: 300)
#   --regress-pct PCT        Regression threshold (default: 25)
#   --skip-cold              Skip cold run
#   --skip-warm              Skip warm run
#
# Exit codes:
#   0 = Success
#   4 = Regression threshold exceeded
#   5 = Setup error

set -euo pipefail

# Detect Python
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "❌ Error: Python 3 not found" >&2
    exit 5
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Locate harness
HARNESS="$REPO_ROOT/tools/ft_bench_harness.py"

if [ ! -f "$HARNESS" ]; then
    echo "❌ Error: Harness not found at $HARNESS" >&2
    exit 5
fi

# Ensure .firsttry directory exists
mkdir -p "$REPO_ROOT/.firsttry"

# Run harness and capture exit code
"$PYTHON" "$HARNESS" "$@" || EXIT_CODE=$?
EXIT_CODE=${EXIT_CODE:-0}

# Interpret exit code
case $EXIT_CODE in
    0)
        echo ""
        echo "✅ Benchmark completed successfully"
        ;;
    4)
        echo ""
        echo "⚠️ Regression threshold exceeded - see report for details"
        ;;
    5)
        echo ""
        echo "❌ Setup error - check environment configuration"
        ;;
    *)
        echo ""
        echo "⚠️ Unexpected exit code: $EXIT_CODE"
        ;;
esac

exit $EXIT_CODE
