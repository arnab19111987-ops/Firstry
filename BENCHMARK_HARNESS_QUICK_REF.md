# FirstTry Benchmark Harness - Quick Reference

## Quick Start

```bash
# Run full benchmark (cold + warm)
./scripts/ft_bench_run.sh

# View human-readable report
cat .firsttry/bench_proof.md

# View machine-readable report
cat .firsttry/bench_proof.json | jq

# View raw logs
cat .firsttry/bench_artifacts/cold.log
cat .firsttry/bench_artifacts/warm.log
```

## Common Commands

### Establish Baseline
```bash
./scripts/ft_bench_run.sh --tier lite --mode fast
mkdir -p reports
cp .firsttry/bench_proof.json reports/baseline-$(date +%Y%m%d).json
```

### Run with Custom Settings
```bash
./scripts/ft_bench_run.sh \
  --tier pro \
  --mode full \
  --max-procs 4 \
  --timeout-s 600 \
  --regress-pct 15
```

### Skip Cold Run (Faster)
```bash
./scripts/ft_bench_run.sh --skip-cold
```

### Skip Warm Run (Baseline Only)
```bash
./scripts/ft_bench_run.sh --skip-warm
```

### Disable Telemetry
```bash
./scripts/ft_bench_run.sh --no-telemetry
```

### Check for Regression
```bash
./scripts/ft_bench_run.sh --regress-pct 10
# Exit code: 0 = no regression, 4 = regressed, 5 = error
```

## Output Files

| File | Purpose |
|------|---------|
| `.firsttry/bench_proof.md` | Human-readable report |
| `.firsttry/bench_proof.json` | Machine-readable data (schema v1) |
| `.firsttry/bench_artifacts/cold.log` | Cold run command + output |
| `.firsttry/bench_artifacts/warm.log` | Warm run command + output |

## JSON Schema (v1)

```json
{
  "schema": 1,
  "timestamp": "2025-11-07T05:24:05Z",
  "host": {
    "os": "Linux",
    "kernel": "6.8.0-1030-azure",
    "arch": "x86_64",
    "cpu_cores": 4,
    "total_ram_gb": 15.6,
    "disk_free_gb": 15.1
  },
  "runs": {
    "cold": {
      "ok": true,
      "elapsed_s": 0.76,
      "exit_code": 0,
      "cache_bytes": 660,
      "cache_files": 3,
      "cache_gb": 0.0,
      "log": "bench_artifacts/cold.log"
    },
    "warm": {
      "ok": true,
      "elapsed_s": 0.28,
      "exit_code": 0,
      "cache_bytes": 660,
      "cache_files": 3,
      "cache_gb": 0.0,
      "log": "bench_artifacts/warm.log"
    }
  },
  "regression": {
    "detected": false,
    "prior_warm_s": 0.25,
    "current_warm_s": 0.28,
    "pct_change": 12.0,
    "threshold_pct": 25.0
  }
}
```

## Interpreting Results

### ✅ Ideal Results
- `elapsed_s`: Cold ~2-5x slower than warm
- `ok`: Both runs true, exit_code 0
- `regression.detected`: false
- Performance stable vs baseline

### ⚠️ Watch For
- Warm slower than cold: Possible cache thrash
- Large cache (>5 GB): Consider `rm -rf .firsttry/cache`
- Large repo (>200k files): Consider `--changed-only` mode
- High variance: Run multiple times, average results

### ❌ Failure Cases
- `ok: false`: Check .log files for errors
- `exit_code: 124`: Timeout exceeded
- `regression.detected: true`: Performance regressed beyond threshold
- `exit_code: 5`: Setup error (missing Python, invalid args)

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (no regression or no baseline) |
| 4 | Regression detected (exceeded threshold) |
| 5 | Setup error (environment/args issue) |

## Integration Examples

### GitHub Actions
```yaml
- name: Benchmark
  run: ./scripts/ft_bench_run.sh --tier lite
  continue-on-error: true

- name: Check Regression
  run: |
    if [ $? -eq 4 ]; then
      echo "Performance regressed!"
      exit 1
    fi
```

### Pre-commit Hook
```yaml
- repo: local
  hooks:
    - id: ft-bench
      name: FirstTry Benchmark
      entry: ./scripts/ft_bench_run.sh --skip-cold
      language: script
      pass_filenames: false
      stages: [manual]
```

### Local Script
```bash
#!/bin/bash
set -eo pipefail

# Run benchmark
./scripts/ft_bench_run.sh --tier lite

# Check for regression
if [ $? -eq 4 ]; then
    echo "❌ Performance regressed!"
    cat .firsttry/bench_proof.md
    exit 1
fi

# Archive report
cp .firsttry/bench_proof.json \
   "reports/bench-$(date +%Y%m%d-%H%M%S).json"
```

## Troubleshooting

### "firsttry: command not found"
```bash
pip install firsttry
# or for dev:
pip install -e .
```

### Warm run slower than cold
- Possible causes: JIT compilation, GC, system contention
- Solution: Run multiple times and average
- Note: This is typically normal on first warm run

### Regression threshold too sensitive
```bash
./scripts/ft_bench_run.sh --regress-pct 50
```

### Cache not populating
```bash
ls -lah .firsttry/cache/
du -sh .firsttry/cache/
```

### Clear cache for fresh run
```bash
rm -rf .firsttry/cache
./scripts/ft_bench_run.sh
```

## Performance Tips

### Reproducible Runs
```bash
export FT_SEND_TELEMETRY=0
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export FT_MAX_PROCS=4
./scripts/ft_bench_run.sh
```

### Minimize Variance
- Run on stable/quiet system
- Multiple runs, take average
- Use `--skip-cold` for quick checks
- Lock CPU frequency if possible

### Archive Baselines
```bash
mkdir -p reports/baselines
git checkout main
./scripts/ft_bench_run.sh
cp .firsttry/bench_proof.json reports/baselines/main.json

git checkout feature-branch
./scripts/ft_bench_run.sh
cp .firsttry/bench_proof.json reports/baselines/feature.json

# Compare
diff -u reports/baselines/main.json reports/baselines/feature.json | jq
```

## References

- Full docs: `BENCHMARK_HARNESS_COMPLETE.md`
- Python harness: `tools/ft_bench_harness.py`
- Shell wrapper: `scripts/ft_bench_run.sh`

---

**Version:** 1.0.0  
**Status:** Production Ready  
**Last Updated:** 2025-11-07
