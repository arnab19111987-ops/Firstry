#!/bin/bash
# FirstTry Benchmark Readiness Shell Wrapper
# Calls the Python auditor and captures output to .firsttry/bench_readiness.md

set -euo pipefail

# Ensure Python exists
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Error: Python not found. Please install Python 3.10+."
    exit 3
fi

# Determine Python executable
PYTHON="${PYTHON3:-python3}"
if ! command -v "$PYTHON" &> /dev/null; then
    PYTHON="python"
fi

if ! command -v "$PYTHON" &> /dev/null; then
    echo "❌ Error: Could not find Python executable."
    exit 3
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Ensure .firsttry directory exists
mkdir -p "$REPO_ROOT/.firsttry"

# Path to the Python auditor (in tools/ directory)
AUDITOR="$REPO_ROOT/tools/ft_readiness_audit.py"

if [ ! -f "$AUDITOR" ]; then
    echo "❌ Error: Auditor script not found at $AUDITOR"
    exit 3
fi

# Output file
OUTPUT_FILE="$REPO_ROOT/.firsttry/bench_readiness.md"

# Run the auditor and capture output
echo "▶️  Running FirstTry Benchmark Readiness Audit..."
echo ""

# Run auditor, tee to both stdout and file
"$PYTHON" "$AUDITOR" 2>&1 | tee "$OUTPUT_FILE"

# Capture exit code from pipe
EXIT_CODE="${PIPESTATUS[0]}"

echo ""
echo "📄 Report saved to: $OUTPUT_FILE"
echo ""

# Translate exit code to status message
case "$EXIT_CODE" in
    0)
        echo "✅ Status: READY - Proceed with benchmarking!"
        ;;
    2)
        echo "⚠️  Status: PARTIAL - Address warnings above for best results"
        ;;
    3)
        echo "❌ Status: BLOCKED - Fix critical issues before proceeding"
        ;;
    *)
        echo "⚠️  Status: UNKNOWN (exit code: $EXIT_CODE)"
        ;;
esac

exit "$EXIT_CODE"
