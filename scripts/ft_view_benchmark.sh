#!/usr/bin/env bash
# Quick view of FT vs Manual benchmark results

set -euo pipefail

SUMMARY=".firsttry/bench/compare_summary.md"
JSON=".firsttry/bench/compare_summary.json"

if [ ! -f "$SUMMARY" ]; then
    echo "❌ No benchmark results found"
    echo "   Run: scripts/ft_vs_manual_sweep.sh && python tools/ft_vs_manual_collate.py"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FirstTry vs Manual Tools Benchmark Results"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cat "$SUMMARY"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Quick Stats"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v python3 >/dev/null 2>&1; then
    python3 <<'PY'
import json
from pathlib import Path

data = json.loads(Path(".firsttry/bench/compare_summary.json").read_text())
rows = data.get("rows", [])

speedups = [r["speedup_x"] for r in rows if r.get("speedup_x")]
if speedups:
    avg_speedup = sum(speedups) / len(speedups)
    print(f"Average speedup: {avg_speedup:.2f}×")
    print(f"Best speedup:    {max(speedups):.2f}× ({[r['tool'] for r in rows if r.get('speedup_x') == max(speedups)][0]})")
    print(f"Worst speedup:   {min(speedups):.2f}× ({[r['tool'] for r in rows if r.get('speedup_x') == min(speedups)][0]})")

parity_ok = sum(1 for r in rows if r.get("parity") == "OK")
parity_total = sum(1 for r in rows if r.get("parity"))
if parity_total > 0:
    print(f"\nParity: {parity_ok}/{parity_total} tools match error counts")

cache_hits = sum(1 for r in rows if r.get("ft_cache_warm") and "hit" in r["ft_cache_warm"])
cache_total = sum(1 for r in rows if r.get("ft_cache_warm"))
if cache_total > 0:
    print(f"Cache hit rate: {cache_hits}/{cache_total} ({100*cache_hits/cache_total:.0f}%)")
PY
fi

echo ""
echo "💡 Files:"
echo "   Summary (MD):  $SUMMARY"
echo "   Summary (JSON): $JSON"
echo "   Logs:          .firsttry/bench/logs/"
echo "   Reports:       .firsttry/bench/reports/"
echo ""
echo "🔄 Rerun: scripts/ft_vs_manual_sweep.sh && python tools/ft_vs_manual_collate.py"
echo ""
