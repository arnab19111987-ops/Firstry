#!/bin/bash
# Check that coverage meets minimum floor
# This runs after pytest --cov generates coverage.json

set -e

if [ ! -f coverage.json ]; then
    echo "Error: coverage.json not found"
    exit 1
fi

# Extract coverage percentage and check floors using Python
python3 - <<'PY'
import json
import sys

CRITICAL_FLOOR = 18.0
WARNING_FLOOR = 20.0

with open("coverage.json") as f:
    data = json.load(f)

pct = data["totals"]["percent_covered"]
print(f"Coverage: {pct:.1f}%")

# Check critical floor (hard failure)
if pct < CRITICAL_FLOOR:
    print(f"❌ CRITICAL: Coverage {pct:.1f}% is below critical floor {CRITICAL_FLOOR}%")
    sys.exit(1)

# Check warning floor (soft warning)
if pct < WARNING_FLOOR:
    print(f"⚠️  WARNING: Coverage {pct:.1f}% is below target {WARNING_FLOOR}%")
    sys.exit(0)

print(f"✅ Coverage {pct:.1f}% meets floor requirements (critical: {CRITICAL_FLOOR}%, target: {WARNING_FLOOR}%)")
sys.exit(0)
PY

