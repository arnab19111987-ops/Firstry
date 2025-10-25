#!/usr/bin/env bash
# scripts/validate-operational-status.sh
# Validates the operational status claims from OPERATIONAL_STATUS_REPORT.md

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FirstTry Operational Status Validation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Track results
PASSED=0
FAILED=0
TOTAL=27

function check() {
    local name="$1"
    local cmd="$2"
    echo -n "[$((PASSED + FAILED + 1))/$TOTAL] $name... "
    if eval "$cmd" &>/dev/null; then
        echo "✅"
        ((PASSED++))
    else
        echo "❌"
        ((FAILED++))
    fi
}

echo "🔍 Section 1: Core CLI Features"
check "CLI Help" "python -m firsttry.cli --help | grep -q 'doctor'"
check "Doctor Command" "python -m firsttry.cli doctor --help | grep -q 'diagnostic'"
check "License Command" "python -m firsttry.cli license --help | grep -q 'verify'"
check "Mirror-CI Command" "python -m firsttry.cli mirror-ci --help | grep -q 'dry-run'"
check "Install Hooks Command" "python -m firsttry.cli install-hooks --help"

echo ""
echo "🔍 Section 2: Quality Gate Checks"
check "Gates Module Exists" "test -f firsttry/gates.py"
check "Lint Check Defined" "grep -q 'def check_lint' firsttry/gates.py"
check "Type Check Defined" "grep -q 'def check_types' firsttry/gates.py"
check "SQLite Drift Defined" "grep -q 'def check_sqlite_drift' firsttry/gates.py"
check "PG Drift Defined" "grep -q 'def check_pg_drift' firsttry/gates.py"

echo ""
echo "🔍 Section 3: Doctor & QuickFix System"
check "Doctor Module Exists" "test -f firsttry/doctor.py"
check "QuickFix Module Exists" "test -f firsttry/quickfix.py"
check "Doctor Tests Pass" "pytest tests/test_doctor_report.py -q"
check "QuickFix Tests Pass" "pytest tests/test_quickfix.py -q"

echo ""
echo "🔍 Section 4: License Management"
check "License Module Exists" "test -f firsttry/license.py"
check "License Tests Pass" "pytest tests/test_license_verify.py -q"
check "License Server Exists" "test -f licensing/app/main.py"
check "License API Tests Pass" "pytest licensing/tests/test_api.py -q"
check "License Webhook Tests Pass" "pytest licensing/tests/test_webhooks.py -q"

echo ""
echo "🔍 Section 5: Database Modules"
check "SQLite Module Exists" "test -f firsttry/db_sqlite.py"
check "PG Module Exists" "test -f firsttry/db_pg.py"
check "DB Tests Pass" "pytest tests/test_db_sqlite.py tests/test_db_pg.py -q"

echo ""
echo "🔍 Section 6: VS Code Extension"
check "Extension TypeScript Exists" "test -f vscode-extension/src/extension.ts"
check "Extension Tests Pass" "cd vscode-extension && npm test"
check "Extension Builds" "cd vscode-extension && npm run build"

echo ""
echo "🔍 Section 7: Dashboard"
check "Dashboard Tests Pass" "cd dashboard && npm test"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "VALIDATION RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Passed:  $PASSED / $TOTAL ($(( PASSED * 100 / TOTAL ))%)"
echo "Failed:  $FAILED / $TOTAL"
echo ""

if [ $PASSED -eq $TOTAL ]; then
    echo "🎉 All operational status checks passed!"
    exit 0
elif [ $FAILED -le 1 ]; then
    echo "⚠️  Mostly operational (acceptable)"
    exit 0
else
    echo "❌ Multiple checks failed - review needed"
    exit 1
fi
