#!/usr/bin/env bash
# Test script for TTY rendering features

set -e

export PYTHONPATH=src

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FirstTry TTY Rendering Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "1️⃣  Testing free-lite tier with --tty (summary only)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python -c "import firsttry.cli as c; c.cmd_run(['--tier','free-lite','--tty'])"
echo ""
echo ""

echo "2️⃣  Testing lite tier with --tty (summary only)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python -c "import firsttry.cli as c; c.cmd_run(['--tier','lite','--tty'])"
echo ""
echo ""

echo "3️⃣  Testing lite tier with --tty-detailed (full report, top 10)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python -c "import firsttry.cli as c; c.cmd_run(['--tier','lite','--tty-detailed'])"
echo ""
echo ""

echo "4️⃣  Testing lite tier with --tty-detailed --tty-max-items 3"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python -c "import firsttry.cli as c; c.cmd_run(['--tier','lite','--tty-detailed','--tty-max-items','3'])"
echo ""
echo ""

echo "✅ All TTY rendering tests completed!"
