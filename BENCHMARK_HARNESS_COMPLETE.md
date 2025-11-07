# FirstTry Benchmark Harness - Complete Documentation

## Overview

The **FirstTry Benchmark Harness** is a production-ready, repo-agnostic tool for executing reproducible cold and warm performance benchmarks of FirstTry CLI runs. It captures comprehensive environment telemetry, detects performance regressions, and emits both human-readable Markdown and machine-parseable JSON reports suitable for CI/CD integration.

## Features

### ✅ Core Capabilities

- **Cold & Warm Benchmark Runs**
  - Cold run: Cache cleared before execution
  - Warm run: Leverages populated cache
  - Accurate wall-clock timing with subprocess capture

- **Comprehensive Environment Capture**
  - OS, kernel, architecture, CPU cores/threads, total RAM
  - Disk free space for repo filesystem
  - Python version, venv detection, executable path
  - First Try version via CLI introspection
  - External toolchain: Node, npm, ruff, pytest, mypy, bandit
  - Git metadata: commit, branch, tag, dirty state

- **Repository Fingerprinting**
  - File count, total size, extension breakdown (top 8)
  - Content-agnostic hash (SHA1) based on file metadata
  - Excludes common non-essential paths (.git, .venv_tmp, __pycache__, etc.)

- **Cache Statistics**
  - Cache directory size in bytes/GB
  - Number of cache files
  - Tracked per run (cold/warm)

- **Dual Output Format**
  - **Markdown**: Human-readable `.firsttry/bench_proof.md` with tables, observations, recommendations
  - **JSON**: Machine-readable `.firsttry/bench_proof.json` with stable schema (v1)
  - **Artifacts**: Raw stdout/stderr logs in `.firsttry/bench_artifacts/`

- **Regression Detection**
  - Compares current warm run vs previous baseline warm time
  - Configurable threshold (default: 25%)
  - Exit code 4 if regression exceeded
  - Detailed change metrics in reports

- **Exit Code System**
  - `0` = Success (no regression or no prior baseline)
  - `4` = Regression threshold exceeded
  - `5` = Setup error (missing Python, invalid args, etc)

## CLI Usage

### Basic Commands

```bash
# Run full benchmark (cold + warm)
./scripts/ft_bench_run.sh

# Cold run only
./scripts/ft_bench_run.sh --skip-warm

# Warm run only (assumes cache exists)
./scripts/ft_bench_run.sh --skip-cold

# Custom configuration
./scripts/ft_bench_run.sh \
  --tier pro \
  --mode full \
  --max-procs 8 \
  --timeout-s 600 \
  --regress-pct 15
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--tier` | Choice (lite\|pro) | lite | FirstTry tier to run |
| `--mode` | Choice (fast\|full) | fast | FirstTry execution mode |
| `--max-procs` | Integer | auto (CPU count, capped at 8) | Parallel processes |
| `--timeout-s` | Integer | 300 | Timeout per run in seconds |
| `--regress-pct` | Float | 25.0 | Regression threshold % |
| `--skip-cold` | Flag | false | Skip cold run |
| `--skip-warm` | Flag | false | Skip warm run |
| `--no-telemetry` | Flag | true | Disable FirstTry telemetry |

### Python Module

Direct invocation:

```bash
python3 tools/ft_bench_harness.py \
  --tier lite \
  --mode fast \
  --max-procs 4 \
  --timeout-s 300 \
  --skip-cold
```

## Output Artifacts

### `.firsttry/bench_proof.md` (Markdown Report)

Human-readable benchmark summary including:

```markdown
# FirstTry Benchmark Report

**Generated:** 2025-11-07T05:24:05.816034Z

## System Snapshot
- OS, kernel, CPU, memory, disk free
- Python version & venv status
- FirstTry version

## Repository Snapshot
- File count, total size, extension breakdown
- Content fingerprint hash

## Benchmark Results
| Run  | Elapsed (s) | Exit Code | Cache (GB) | Cache Files |
|------|-------------|-----------|------------|-------------|
| cold | 0.76        | 0         | 0.0        | 3           |
| warm | 0.28        | 0         | 0.0        | 3           |

## Observations
✅ Warm run is faster than cold (cache effective)

## Regression Status
✅ No Regression (change: -72.0% vs baseline)

## Recommended Environment
```bash
export FT_MAX_PROCS=2
export FT_TIMEOUT_S=60
export FT_SEND_TELEMETRY=0
```

## Toolchain Versions
- ruff: ruff 0.14.3
- pytest: pytest 8.4.2
- mypy: mypy 1.18.2
...

## Git Info
- Commit: c66a354...
- Branch: main
- Dirty: No
```

### `.firsttry/bench_proof.json` (Machine-Readable Report)

Stable schema (v1) for CI/CD integration:

```json
{
  "schema": 1,
  "timestamp": "2025-11-07T05:24:05.816034Z",
  "host": {
    "os": "Linux",
    "kernel": "6.8.0-1030-azure",
    "arch": "x86_64",
    "cpu_cores": 4,
    "cpu_threads": 4,
    "total_ram_gb": 15.6,
    "disk_free_gb": 15.1
  },
  "python": {
    "version": "3.11.7",
    "executable": "/usr/local/python/current/bin/python3",
    "venv_active": false
  },
  "firsttry": {
    "version": "unknown",
    "tier": "lite",
    "mode": "fast"
  },
  "tooling": {
    "node": "v20.19.5",
    "npm": "10.8.2",
    "ruff": "ruff 0.14.3",
    "pytest": "pytest 8.4.2",
    "mypy": "mypy 1.18.2 (compiled: yes)",
    "bandit": "bandit 1.8.3"
  },
  "git": {
    "commit": "c66a354898e26a59ed3729aea63f726fd4ec5b40",
    "branch": "main",
    "tag": null,
    "dirty": true
  },
  "env": {
    "FT_MAX_PROCS": 2,
    "FT_TIMEOUT_S": 60,
    "FT_SEND_TELEMETRY": 0
  },
  "repo": {
    "file_count": 2964,
    "total_bytes": 42053657,
    "total_gb": 0.039,
    "fingerprint_hash": "b272bdcaf218d9e2",
    "top_extensions": [
      {"ext": ".py", "count": 2092},
      {"ext": ".no_ext", "count": 425}
    ]
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
    "prior_warm_s": 0.15,
    "current_warm_s": 0.28,
    "pct_change": 93.3,
    "threshold_pct": 25.0
  }
}
```

### `.firsttry/bench_artifacts/` (Raw Logs)

- `cold.log` - Full stdout/stderr from cold run
- `warm.log` - Full stdout/stderr from warm run

Example log:
```
=== COMMAND ===
/usr/local/python/current/bin/python3 -m firsttry run fast --tier lite --show-report --no-remote-cache

=== STDOUT ===
[timing data and FirstTry output]

=== STDERR ===
[any warnings or diagnostics]
```

## Integration Examples

### GitHub Actions

```yaml
name: Benchmark

on:
  push:
    branches: [main]
  pull_request:

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Benchmark
        run: ./scripts/ft_bench_run.sh --tier lite
        continue-on-error: true
      
      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: bench-report
          path: .firsttry/bench_proof.*
      
      - name: Check Regression
        run: |
          EXIT_CODE=$?
          if [ $EXIT_CODE -eq 4 ]; then
            echo "❌ Performance regression detected!"
            cat .firsttry/bench_proof.md
            exit 1
          fi
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: ft-bench
      name: FirstTry Benchmark
      entry: ./scripts/ft_bench_run.sh --skip-cold
      language: script
      pass_filenames: false
      always_run: true
      stages: [manual]
```

### Local CI Script

```bash
#!/bin/bash
set -eo pipefail

# Run benchmark with regression check
./scripts/ft_bench_run.sh --tier lite --regress-pct 20

# Show report
cat .firsttry/bench_proof.md

# Archive for trend analysis
cp .firsttry/bench_proof.json \
   "reports/bench-$(date +%Y%m%d-%H%M%S).json"
```

## Performance Characteristics

### Cold Run
- Clears `.firsttry/cache` before execution
- FirstTry CLI must rebuild all check results from scratch
- Typical duration: 0.5-10s (repo dependent)
- Cache populated after run

### Warm Run
- Reuses populated cache from cold run
- FirstTry CLI serves most results from cache
- Typical duration: 0.1-2s (repo dependent)
- Should be **significantly faster** than cold run

### Regression Thresholds

- **Default threshold: 25%** - Catches meaningful slowdowns
- **For high-variance environments: 50%** - More tolerant
- **For strict benchmarks: 10%** - Catches any regression

## Observations & Warnings

The harness automatically reports:

✅ **Cache Effective** - Warm is faster than cold (expected)
⚠️ **Warm Slower than Cold** - Suggests cache thrash or lock contention
⚠️ **Large Cache** (>5 GB) - Recommend purging: `rm -rf .firsttry/cache`
ℹ️ **Large Repo** (>200k files) - Consider `--changed-only` mode

## Reproducibility & Best Practices

### Ensure Reproducible Runs

```bash
# Disable telemetry for benchmarking
export FT_SEND_TELEMETRY=0

# Disable plugin autoload in pytest
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

# Lock parallelism
export FT_MAX_PROCS=4

# Fixed timeout
export FT_TIMEOUT_S=300

# Run benchmark
./scripts/ft_bench_run.sh
```

### Interpreting Trends

- Save JSON reports with timestamps: `reports/bench-$(date +%Y%m%d).json`
- Compare across commits to identify performance impacts
- Account for external factors (system load, garbage collection)
- Average multiple runs for stability

### Cache Strategy

- **Persistent Cache**: Warm runs benefit from previous cold runs
- **Fresh Cache**: Use `--skip-warm` on first run to establish baseline
- **Cache Invalidation**: If FirstTry or tools updated, clear cache: `rm -rf .firsttry/cache`

## Implementation Details

### Python Dependencies

**Stdlib only** (Python 3.11+):
- `argparse`, `subprocess`, `os`, `sys`, `json`, `time`, `platform`, `shutil`
- `hashlib`, `pathlib`, `textwrap`, `datetime`, `typing`

### Repo Fingerprint Algorithm

1. Walk repo tree excluding non-essential paths
2. Sum file count, total bytes, modification times
3. Compute SHA1 hash of concatenated metadata
4. Store first 16 hex chars as fingerprint

Rationale: Content-agnostic but volatile to file changes

### Cache Stats Collection

- Recursively walk `.firsttry/cache/`
- Sum file sizes and count entries
- Report in both bytes and GB

## Troubleshooting

### Issue: `firsttry: command not found`

**Solution:** Ensure FirstTry is installed:
```bash
pip install firsttry
# or for dev
pip install -e .
```

### Issue: Cold run slower than warm run

**Solution:** Possible causes:
- Initial JIT compilation in Python
- Garbage collection during cold run
- System contention during cold run

Run multiple times and average.

### Issue: Cache not populating

**Solution:** Check `.firsttry/cache/` directory:
```bash
ls -lah .firsttry/cache/
du -sh .firsttry/cache/
```

If empty or stale, ensure runs succeed with exit code 0.

### Issue: Regression threshold too sensitive

**Solution:** Adjust with `--regress-pct`:
```bash
./scripts/ft_bench_run.sh --regress-pct 50  # More tolerant
```

## Files

- `tools/ft_bench_harness.py` - Main Python harness (828 lines, stdlib only)
- `scripts/ft_bench_run.sh` - POSIX shell wrapper (executable)
- `.firsttry/bench_proof.md` - Generated Markdown report
- `.firsttry/bench_proof.json` - Generated JSON report (schema v1)
- `.firsttry/bench_artifacts/cold.log` - Cold run log
- `.firsttry/bench_artifacts/warm.log` - Warm run log

## Version & Status

- **Version:** 1.0.0
- **Status:** Production Ready
- **Last Updated:** 2025-11-07
- **Maintainer:** FirstTry Team

## License

Same as FirstTry CLI

---

**Questions?** Check the JSON schema or run `./scripts/ft_bench_run.sh --help` (via Python harness).
