#!/usr/bin/env bash
# Quick peek at tier sweep results

set -euo pipefail

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FirstTry Tier Sweep Results Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Count artifacts
REPORTS=$(ls .firsttry/reports/*.json 2>/dev/null | wc -l)
LOGS=$(ls .firsttry/logs/*.log 2>/dev/null | wc -l)
HISTORY=$(wc -l < .firsttry/history.jsonl 2>/dev/null || echo 0)

echo "📊 Artifact Counts:"
echo "   Reports:  $REPORTS files in .firsttry/reports/"
echo "   Logs:     $LOGS files in .firsttry/logs/"
echo "   History:  $HISTORY runs in .firsttry/history.jsonl"
echo ""

# Check if summary exists
if [ -f .firsttry/tier_summary.md ]; then
    echo "📝 Tier Summary (.firsttry/tier_summary.md):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    cat .firsttry/tier_summary.md
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "⚠️  No summary found. Run: python tools/ft_collate_reports.py"
fi

echo ""
echo "🔍 Quick Stats:"
if [ "$REPORTS" -gt 0 ]; then
    # Extract tier/phase counts
    echo "   Tiers tested:"
    ls .firsttry/reports/*.json | xargs basename -a | cut -d_ -f2 | sort -u | sed 's/^/     - /'
    
    echo "   Latest reports:"
    ls -t .firsttry/reports/*.json | head -3 | xargs basename -a | sed 's/^/     - /'
else
    echo "   No reports yet. Run: scripts/ft_tier_sweep.sh"
fi

echo ""
echo "💡 Next Steps:"
echo "   - View full summary:  cat .firsttry/tier_summary.md"
echo "   - Rerun sweep:        scripts/ft_tier_sweep.sh"
echo "   - Rebuild summary:    python tools/ft_collate_reports.py"
echo "   - View latest log:    ls -t .firsttry/logs/*.log | head -1 | xargs cat"
echo ""
