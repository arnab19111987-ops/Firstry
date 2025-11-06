#!/usr/bin/env bash
# One-liner to sweep and view results

set -e

echo "🚀 Running full tier sweep..."
scripts/ft_tier_sweep.sh

echo ""
echo "📊 Generating summary..."
python tools/ft_collate_reports.py

echo ""
echo "✅ Complete! Viewing results..."
echo ""
scripts/ft_tier_summary.sh
