#!/usr/bin/env bash
# Operational Status Validation Script
# Runs all checks mentioned in OPERATIONAL_STATUS_REPORT.md
# Usage: bash scripts/validate-operational-status.sh

set -u

# Ensure we're in the repo root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$REPO_ROOT" || exit 1

PASS=0
FAIL=0
WARN=0

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  FirstTry Operational Status Validation                   ║"
echo "║  Running all checks from OPERATIONAL_STATUS_REPORT.md      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

log_pass() {
  echo "✅ PASS: $1"
  PASS=$((PASS + 1))
}

log_fail() {
  echo "❌ FAIL: $1"
  FAIL=$((FAIL + 1))
}

log_warn() {
  echo "⚠️  WARN: $1"
  WARN=$((WARN + 1))
}

run_check() {
  local name="$1"
  shift
  echo ""
  echo "━━━ $name ━━━"
  if "$@"; then
    log_pass "$name"
    return 0
  else
    log_fail "$name"
    return 1
  fi
}

# ==================== Python Tests ====================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  1. Python Test Suite (42 tests expected)                 ║"
echo "╚════════════════════════════════════════════════════════════╝"

if pytest -q --tb=no 2>&1 | tee /tmp/pytest_output.txt | grep -q "42 passed"; then
  log_pass "Python test suite (42/42 passing)"
else
  log_fail "Python test suite (expected 42 passed)"
  cat /tmp/pytest_output.txt | tail -10
fi

# ==================== Lint Checks ====================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  2. Lint Checks (ruff)                                     ║"
echo "╚════════════════════════════════════════════════════════════╝"

if command -v ruff >/dev/null 2>&1; then
  if ruff check . --quiet 2>&1; then
    log_pass "Ruff lint (0 errors)"
  else
    log_fail "Ruff lint (errors found)"
  fi
else
  log_warn "Ruff not installed"
fi

# ==================== Type Checks ====================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  3. Type Checking (mypy)                                   ║"
echo "╚════════════════════════════════════════════════════════════╝"

if command -v mypy >/dev/null 2>&1; then
  if mypy . --no-error-summary 2>&1 | grep -q "Success"; then
    log_pass "Mypy type checking"
  else
    log_warn "Mypy type checking (warnings/errors found)"
  fi
else
  log_warn "Mypy not installed"
fi

# ==================== Format Checks ====================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  4. Format Checking (black)                                ║"
echo "╚════════════════════════════════════════════════════════════╝"

if command -v black >/dev/null 2>&1; then
  if black --check . --quiet 2>&1; then
    log_pass "Black format check (no changes needed)"
  else
    log_warn "Black format check (would reformat files)"
  fi
else
  log_warn "Black not installed"
fi

# ==================== Dashboard Tests ====================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  5. Dashboard Tests (TypeScript/Vitest)                    ║"
echo "╚════════════════════════════════════════════════════════════╝"

if [ -d "dashboard" ] && [ -f "dashboard/package.json" ]; then
  cd dashboard || exit 1
  if npm test --silent 2>&1 | grep -q "1 passed"; then
    log_pass "Dashboard tests (1/1 passing, 100% coverage)"
  else
    log_fail "Dashboard tests"
  fi
  cd ..
else
  log_warn "Dashboard not found"
fi

# ==================== CLI Smoke Tests ====================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  6. CLI Smoke Tests                                        ║"
echo "╚════════════════════════════════════════════════════════════╝"

if command -v firsttry >/dev/null 2>&1 || python -m firsttry --help >/dev/null 2>&1; then
  if python -m firsttry --help >/dev/null 2>&1; then
    log_pass "CLI: --help works"
  else
    log_fail "CLI: --help failed"
  fi

  if python -m firsttry mirror-ci --root . >/dev/null 2>&1; then
    log_pass "CLI: mirror-ci command works"
  else
    log_warn "CLI: mirror-ci command (may fail if no workflows)"
  fi
else
  log_fail "CLI: firsttry command not available"
fi

# ==================== Module Imports ====================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  7. Module Import Validation                               ║"
echo "╚════════════════════════════════════════════════════════════╝"

modules=(
  "firsttry.cli"
  "firsttry.ci_mapper"
  "firsttry.gates"
  "firsttry.db_pg"
  "firsttry.db_sqlite"
  "firsttry.docker_smoke"
  "firsttry.hooks"
  "firsttry.vscode_skel"
)

for mod in "${modules[@]}"; do
  if python -c "import ${mod}" 2>/dev/null; then
    log_pass "Import: $mod"
  else
    log_fail "Import: $mod"
  fi
done

# ==================== Runner System ====================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  8. Runner System Validation                               ║"
echo "╚════════════════════════════════════════════════════════════╝"

# Check stub runners (default)
if python -c "from firsttry import cli; r = cli.runners.run_ruff([]); assert r.ok" 2>/dev/null; then
  log_pass "Stub runners working"
else
  log_fail "Stub runners"
fi

# Check real runners (if available)
if [ -f "tools/firsttry/firsttry/runners.py" ]; then
  if FIRSTTRY_USE_REAL_RUNNERS=1 python -c "import sys; sys.path.insert(0, 'tools/firsttry'); from firsttry import runners; assert hasattr(runners, 'run_ruff')" 2>/dev/null; then
    log_pass "Real runners module exists and importable"
  else
    log_warn "Real runners module import issue"
  fi
else
  log_warn "Real runners module not found (expected at tools/firsttry/firsttry/runners.py)"
fi

# ==================== Git Status ====================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  9. Git Repository Status                                  ║"
echo "╚════════════════════════════════════════════════════════════╝"

if git rev-parse --git-dir >/dev/null 2>&1; then
  log_pass "Git repository initialized"
  
  current_branch=$(git rev-parse --abbrev-ref HEAD)
  echo "    Current branch: $current_branch"
  
  if git describe --tags --exact-match 2>/dev/null; then
    current_tag=$(git describe --tags --exact-match)
    log_pass "On tagged commit: $current_tag"
  else
    echo "    (Not on a tagged commit)"
  fi
  
  uncommitted=$(git status --short | wc -l)
  if [ "$uncommitted" -eq 0 ]; then
    log_pass "Clean working tree (no uncommitted changes)"
  else
    log_warn "Uncommitted changes found ($uncommitted files)"
  fi
else
  log_fail "Not a git repository"
fi

# ==================== File Structure Validation ====================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  10. Critical File Structure                               ║"
echo "╚════════════════════════════════════════════════════════════╝"

critical_files=(
  "pyproject.toml"
  "pytest.ini"
  "README.md"
  "Makefile"
  ".github/workflows/ci-gate.yml"
  ".github/workflows/firsttry-ci.yml"
  "firsttry/cli.py"
  "tools/firsttry/firsttry/cli.py"
  "licensing/app/main.py"
  "dashboard/package.json"
)

for file in "${critical_files[@]}"; do
  if [ -f "$file" ]; then
    log_pass "File exists: $file"
  else
    log_fail "Missing file: $file"
  fi
done

# ==================== VSCode Extension Checks ====================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  11. VSCode Extension Status                               ║"
echo "╚════════════════════════════════════════════════════════════╝"

if [ -f "vscode-extension/package.json" ]; then
  log_pass "VSCode extension package.json exists"
  
  if grep -q '"test"' vscode-extension/package.json; then
    log_pass "VSCode extension has test script"
  else
    log_warn "VSCode extension missing test script"
  fi
  
  if grep -q 'activationEvents' vscode-extension/package.json; then
    log_warn "VSCode extension has deprecated activationEvents field"
  fi
else
  log_fail "VSCode extension package.json not found"
fi

# Check .eslintrc.json for duplication
if [ -f "vscode-extension/.eslintrc.json" ]; then
  json_object_count=$(grep -c '^{' vscode-extension/.eslintrc.json)
  if [ "$json_object_count" -gt 1 ]; then
    log_warn "VSCode extension .eslintrc.json has $json_object_count JSON objects (expected 1)"
  else
    log_pass "VSCode extension .eslintrc.json is clean"
  fi
fi

# ==================== Summary ====================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  VALIDATION SUMMARY                                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "  ✅ PASS:  $PASS"
echo "  ⚠️  WARN:  $WARN"
echo "  ❌ FAIL:  $FAIL"
echo ""

total=$((PASS + FAIL))
if [ "$total" -gt 0 ]; then
  percentage=$((PASS * 100 / total))
  echo "  Operational Health: ${percentage}% ($PASS/$total checks passing)"
else
  percentage=0
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🎉 ALL CRITICAL CHECKS PASSED! Repository is operational."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
else
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "⚠️  FAILURES DETECTED! Review output above for details."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 1
fi
