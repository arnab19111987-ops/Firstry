# FirstTry Tier Sweep & Reporting System

## Quick Start

```bash
# 1. Run tier sweep (all tiers, cold + warm)
scripts/ft_tier_sweep.sh

# 2. Generate summary reports
python tools/ft_collate_reports.py

# 3. View summary
cat .firsttry/tier_summary.md
```

## What Gets Generated

### Per-Run Artifacts
- **Reports**: `.firsttry/reports/<timestamp>_<tier>_<phase>.json`
  - JSON report for each tier/phase combination
  - Contains check statuses, durations, cache hits
  
- **Logs**: `.firsttry/logs/<timestamp>_<tier>_<phase>.log`
  - Full console output for each run
  - Useful for debugging failures

- **History**: `.firsttry/history.jsonl`
  - Append-only log of all runs
  - One JSON line per run

### Summary Artifacts
- **JSON Summary**: `.firsttry/tier_summary.json`
  - Aggregated stats per tier (cold/warm)
  - p50/p95 latencies, cache hit rates
  - Regression flags, slowest checks
  
- **Markdown Summary**: `.firsttry/tier_summary.md`
  - Human-readable tier summary
  - Quick overview of performance

## Usage Examples

### Run Specific Tiers Only

```bash
# Just free tiers
TIERS="free-lite lite" scripts/ft_tier_sweep.sh

# Just paid tiers
TIERS="pro strict" scripts/ft_tier_sweep.sh

# Single tier
TIERS="lite" scripts/ft_tier_sweep.sh
```

### Custom Output Directories

```bash
# Save to custom locations
OUTDIR=/tmp/ft-reports LOGDIR=/tmp/ft-logs scripts/ft_tier_sweep.sh
```

### Rebuild Summary After New Runs

```bash
# Add more runs to .firsttry/reports/, then:
python tools/ft_collate_reports.py
```

### View Latest Summary

```bash
# First 120 lines
sed -n '1,120p' .firsttry/tier_summary.md

# Full summary
cat .firsttry/tier_summary.md
```

## Interpreting Results

### Tier Summary Fields

```json
{
  "tiers": {
    "lite": {
      "cold": {
        "count": 3,           // Total checks run
        "ok": 2,              // Passed checks
        "fail": 1,            // Failed checks
        "p50_ms": 401,        // Median duration
        "p95_ms": 1028,       // 95th percentile
        "checks": {...}       // Per-check details
      },
      "warm": {
        "cache_hit_rate": 0.33,  // 33% of checks from cache
        ...
      },
      "regression_flag": false   // Warm >25% slower than cold
    }
  }
}
```

### What to Look For

✅ **Good Signs**:
- High cache hit rate on warm runs (>50%)
- Low p95 latencies (<2000ms for most tiers)
- No regression flags
- All checks passing (ok count == total count)

⚠️ **Warning Signs**:
- Low cache hit rate (<30%)
- Regression flag = true (warm slower than cold)
- High fail counts
- p95 > 5000ms (very slow checks)

## Copilot Analysis Prompt

After running the sweep and collation, use this prompt with GitHub Copilot Chat:

```
You are auditing the FirstTry CLI across tiers.

Context you can read from the repo:
- Per-run JSON reports are in `.firsttry/reports/*.json` (names like `<timestamp>_<tier>_<phase>.json`).
- A collated summary is in `.firsttry/tier_summary.json` and `.firsttry/tier_summary.md`.
- Historical runs are appended to `.firsttry/history.jsonl`.
- Console logs for each run are in `.firsttry/logs/*.log`.

Your tasks:
1) Parse `.firsttry/tier_summary.json`. For each tier, compute and confirm:
   - cold p50/p95 (ms), warm p50/p95 (ms)
   - warm cache hit rate
   - count of ok/fail/skip/error (cold vs warm)
   - top 3 slow checks on warm, with durations and cache_status

2) Cross-check with `.firsttry/history.jsonl` for the latest 5 runs per tier:
   - trends in cache hit rate, any increasing durations
   - list any checks that frequently fail or time out

3) If any tier shows `regression_flag=true` in the summary, identify which checks likely caused it,
   by comparing cold vs warm durations per check and inspecting logs in `.firsttry/logs/`.

4) Produce a clean Markdown report with:
   - An executive summary (one paragraph)
   - A table per tier: {check id, cold ms, warm ms, cache_status(warm), status(warm)}
   - A "Findings" section: bullets for slow or flaky checks; timeouts; missing tools (if seen); environment oddities
   - A "Recommendations" section with prioritized, concrete fixes (e.g., raise/trim timeouts, make tests lint-clean to enable caching, exclude heavy paths, increase workers, or enable remote cache)
   - A "Next actions" checklist with CLI commands to reproduce (use `ft run --tier <tier> --show-report`)

5) Keep it concise and actionable. When uncertain, cite file paths you used (reports/logs) so someone can verify quickly.
```

## One-Liner Cheat Sheet

```bash
# Full sweep → summary → view
scripts/ft_tier_sweep.sh && python tools/ft_collate_reports.py && cat .firsttry/tier_summary.md

# Quick re-sweep of two tiers
TIERS="free-lite lite" scripts/ft_tier_sweep.sh

# Rebuild summary after manual runs
python tools/ft_collate_reports.py

# View all report files
ls -lh .firsttry/reports/

# View latest log
ls -t .firsttry/logs/*.log | head -1 | xargs cat

# Count total runs
ls .firsttry/reports/*.json | wc -l

# View history (last 10 runs)
tail -10 .firsttry/history.jsonl | python -m json.tool
```

## Integration with CI

```yaml
# Example GitHub Actions workflow
- name: Run tier sweep
  run: scripts/ft_tier_sweep.sh

- name: Generate summary
  run: python tools/ft_collate_reports.py

- name: Upload artifacts
  uses: actions/upload-artifact@v3
  with:
    name: tier-reports
    path: |
      .firsttry/reports/
      .firsttry/logs/
      .firsttry/tier_summary.json
      .firsttry/tier_summary.md
```

## Troubleshooting

### No reports generated
```bash
# Check if ft wrapper exists
test -x .venv/bin/ft && echo "✅ OK" || echo "❌ Create with: cat > .venv/bin/ft <<'SH'
#!/usr/bin/env bash
export PYTHONPATH=src
exec python -m firsttry.cli \"\$@\"
SH
chmod +x .venv/bin/ft"
```

### Collation fails
```bash
# Check reports exist
ls .firsttry/reports/*.json || echo "Run sweep first: scripts/ft_tier_sweep.sh"

# Validate JSON
for f in .firsttry/reports/*.json; do
  python -m json.tool "$f" > /dev/null || echo "Invalid: $f"
done
```

### Missing data in summary
```bash
# Re-run specific tier
TIERS="lite" scripts/ft_tier_sweep.sh

# Force fresh run (clear cache)
rm -rf .firsttry/cache/
TIERS="lite" scripts/ft_tier_sweep.sh
```
