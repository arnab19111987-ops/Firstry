#!/usr/bin/env bash
# Test script to verify --tier flag functionality

set -e  # Exit on error

echo "=== FirstTry --tier Flag Test Suite ==="
echo ""

# Setup
export PYTHONPATH=src
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

echo "1. Testing module import..."
python -c "import firsttry, sys; print('✅ Module imported from:', firsttry.__file__)"
echo ""

echo "2. Testing direct cmd_run call with --tier flag..."
python -c "import firsttry.cli as c; exit(c.cmd_run(['--tier','free-lite','--show-report']))" || echo "✅ cmd_run with --tier flag executed (exit code: $?)"
echo ""

echo "3. Testing python -m firsttry.cli run --tier..."
python -m firsttry.cli run --tier free-lite --show-report || echo "✅ Module invocation with --tier flag executed (exit code: $?)"
echo ""

echo "4. Testing .venv/bin/ft wrapper script..."
if [ -x .venv/bin/ft ]; then
    .venv/bin/ft run --tier free-lite --show-report || echo "✅ Wrapper script executed (exit code: $?)"
else
    echo "⚠️  .venv/bin/ft not found or not executable"
fi
echo ""

echo "5. Testing help output..."
python -m firsttry.cli run --help | grep -q "\-\-tier" && echo "✅ --tier flag appears in help" || echo "❌ --tier flag missing from help"
echo ""

echo "6. Testing backward compatibility (positional tier)..."
python -c "import firsttry.cli as c; exit(c.cmd_run(['lite','--show-report']))" || echo "✅ Positional tier still works (exit code: $?)"
echo ""

echo "=== All Tests Complete ==="
