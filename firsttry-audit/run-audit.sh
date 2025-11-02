#!/bin/bash
# FirstTry Project Audit Script
# Runs comprehensive capability and health checks
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT_DIR="$REPO_ROOT/firsttry-audit"
RAW_LOG="$AUDIT_DIR/firsttry-audit-raw.log"

cd "$REPO_ROOT"

echo "Starting FirstTry project audit..." | tee "$RAW_LOG"
echo "Repository: $REPO_ROOT" | tee -a "$RAW_LOG"
echo "Date: $(date)" | tee -a "$RAW_LOG"
echo "============================================" | tee -a "$RAW_LOG"

# Step 1: Repository info
echo -e "\n### Step 1: Repository Info ###" | tee -a "$RAW_LOG"
pwd | tee -a "$RAW_LOG"
git rev-parse --abbrev-ref HEAD | tee -a "$RAW_LOG"

# Step 2: Python info
echo -e "\n### Step 2: Python Info ###" | tee -a "$RAW_LOG"
python -V | tee -a "$RAW_LOG"
pip -V | tee -a "$RAW_LOG"

# Step 3: Import test
echo -e "\n### Step 3: Import Test ###" | tee -a "$RAW_LOG"
PYTHONPATH=src python -c "import firsttry; print('IMPORT_OK')" 2>&1 | tee -a "$RAW_LOG"

# Step 4: CLI help
echo -e "\n### Step 4: CLI Help ###" | tee -a "$RAW_LOG"
PYTHONPATH=src python -m firsttry --help 2>&1 | tee -a "$RAW_LOG"

# Step 5: Command tests
echo -e "\n### Step 5: Command Tests ###" | tee -a "$RAW_LOG"
echo "--- inspect ---" | tee -a "$RAW_LOG"
PYTHONPATH=src timeout 30 python -m firsttry inspect 2>&1 | tee -a "$RAW_LOG" || echo "FAILED" | tee -a "$RAW_LOG"

echo "--- sync ---" | tee -a "$RAW_LOG"
PYTHONPATH=src timeout 30 python -m firsttry sync 2>&1 | tee -a "$RAW_LOG" || echo "FAILED" | tee -a "$RAW_LOG"

echo "--- version ---" | tee -a "$RAW_LOG"
PYTHONPATH=src python -m firsttry version 2>&1 | tee -a "$RAW_LOG" || echo "FAILED" | tee -a "$RAW_LOG"

# Step 6: Test legacy commands
echo -e "\n### Step 6: Legacy Commands ###" | tee -a "$RAW_LOG"
for cmd in status setup doctor report; do
    echo "--- firsttry $cmd ---" | tee -a "$RAW_LOG"
    PYTHONPATH=src python -m firsttry "$cmd" 2>&1 | tee -a "$RAW_LOG" || echo "Command $cmd failed" | tee -a "$RAW_LOG"
done

# Step 7: Code searches
echo -e "\n### Step 7: License Code Search ###" | tee -a "$RAW_LOG"
grep -r "license\|licen[cs]e\|trial" src/ --include="*.py" -i | head -20 | tee -a "$RAW_LOG" || echo "No license matches" | tee -a "$RAW_LOG"

echo -e "\n### Step 8: Hook Installation Search ###" | tee -a "$RAW_LOG"
grep -r "pre-commit\|pre-push\|install_hooks" src/ --include="*.py" | head -10 | tee -a "$RAW_LOG" || echo "No hook matches" | tee -a "$RAW_LOG"

# Step 9: Config files
echo -e "\n### Step 9: Configuration Files ###" | tee -a "$RAW_LOG"
find . -name "firsttry.toml" -o -name "pyproject.toml" -o -name "package.json" | grep -v ".mypy_cache\|node_modules\|\.git" | tee -a "$RAW_LOG"

# Step 10: Test run
echo -e "\n### Step 10: Test Results ###" | tee -a "$RAW_LOG"
timeout 60 python -m pytest --tb=no 2>&1 | tail -10 | tee -a "$RAW_LOG" || echo "Tests failed to complete" | tee -a "$RAW_LOG"

# Step 11: Network calls
echo -e "\n### Step 11: Network Call Search ###" | tee -a "$RAW_LOG"
grep -r "requests\|httpx\|urllib\|aiohttp" src/ --include="*.py" | head -10 | tee -a "$RAW_LOG" || echo "No network calls found" | tee -a "$RAW_LOG"

# Step 12: Cache paths
echo -e "\n### Step 12: License Cache Paths ###" | tee -a "$RAW_LOG"
grep -r "CACHE_PATH\|\.firsttry.*license" src/ --include="*.py" | tee -a "$RAW_LOG" || echo "No cache paths found" | tee -a "$RAW_LOG"

echo -e "\nAudit completed. Check $RAW_LOG for full output." | tee -a "$RAW_LOG"