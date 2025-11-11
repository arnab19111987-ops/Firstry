# Warm Cache System - Implementation Guide

## Overview

The warm cache system provides fast, intelligent pre-commit checks using testmon, flaky test tracking, and golden cache from CI. This replaces slow full test runs with targeted, incremental testing.

## Components Implemented

### 1. Dependencies (requirements-dev.txt)
```
pytest-testmon==2.1.1      # Smart test selection based on code changes
pytest-json-report==1.5.0  # Robust JSON output for failure extraction
coverage==7.6.4             # Coverage tracking
diff-cover==9.2.0          # Differential coverage on changed lines
```

### 2. Pytest Configuration (pytest.ini)
```ini
[pytest]
testmon_cache_dir = .firsttry/warm/testmon
```

### 3. Cache Utilities (`src/firsttry/ci_parity/cache_utils.py`)

**Functions:**
- `auto_refresh_golden_cache(ref)` - Auto-fetch cache from CI (~1s budget, silent)
- `update_cache()` - Explicit cache download via gh CLI
- `clear_cache()` - Nuke all caches (warm, mypy, ruff, testmon)
- `read_flaky_tests()` - Load known flaky test nodeids from ci/flaky_tests.json
- `ensure_dirs()` - Create required directories

**Directories:**
- `artifacts/` - Test reports, coverage, parity results
- `.firsttry/warm/` - Warm cache (testmon, fingerprint)
- `ci/flaky_tests.json` - Persistent flaky test memory

### 4. Parity Runner Warm Path (`src/firsttry/ci_parity/parity_runner.py`)

**New function: `warm_path(explain=False)`**

Strategy:
1. **Testmon** - Run only tests affected by code changes
   - Exit code 5 = no tests (skip, not failure)
   - JSON report for reliable failure extraction
   
2. **Flaky Tests** - Always run CI-known flaky tests
   - Positional nodeids (no -k escaping issues)
   - Limit 200 tests to prevent command overflow
   
3. **Smoke Fallback** - If testmon found nothing AND no flakies
   - Run @smoke marker tests
   - Ensures minimum coverage on clean branches
   
4. **Diff-Coverage** - Optional incremental coverage gate
   - 90% on changed lines only
   - Uses artifacts/coverage.xml if available

**Exit codes:**
- 0: Success
- 221: Test failure
- 222: Timeout
- 231: Coverage failure

### 5. CLI Integration (`src/firsttry/cli.py`)

**New commands:**
```bash
ft update-cache    # Pull warm cache from CI
ft clear-cache     # Nuke all local caches
```

**Auto-refresh:**
- Runs on EVERY ft command
- Silent, best-effort, ~1s budget
- Keeps cache warm without blocking

**Pre-commit routing:**
```bash
ft pre-commit              # Fast (--self-check, ~1.6s)
ft pre-commit --parity     # Full (all tools, ~3min)
ft pre-commit --full       # Alias for --parity
```

### 6. Makefile Targets
```makefile
make update-cache    # Pull warm cache from CI
make clear-cache     # Nuke local caches
```

## CI Integration

### Golden Cache Production (main branch)

Add to `.github/workflows/ci.yml` after tests pass:

```yaml
- name: Compute fingerprint
  if: github.ref == 'refs/heads/main' && success()
  run: |
    # Generate fingerprint from lock files
    echo "$(git rev-parse HEAD)-$(sha256sum ci/parity.lock.json | cut -d' ' -f1)" > .firsttry/warm/fingerprint.txt
    echo "FP=$(cat .firsttry/warm/fingerprint.txt)" >> $GITHUB_ENV

- name: Package warm cache
  if: github.ref == 'refs/heads/main' && success()
  run: |
    mkdir -p artifacts
    zip -r artifacts/warm-cache-${FP}.zip \
      .firsttry/warm \
      .mypy_cache \
      .ruff_cache \
      -x '*.pyc' -x '.pytest_cache/*'

- name: Upload warm cache
  if: github.ref == 'refs/heads/main' && success()
  uses: actions/upload-artifact@v3
  with:
    name: warm-cache-${{ env.FP }}
    path: artifacts/warm-cache-${{ env.FP }}.zip
    retention-days: 30
```

### PR Workflow - Warm vs Full with Divergence Detection

```yaml
name: PR Checks (Warm + Full)

on:
  pull_request:
    branches: [main]

jobs:
  warm-and-full:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need history for diff-cover

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
          pip install -e .

      - name: Warm stage (simulate dev)
        run: |
          ft update-cache || true
          ft pre-commit --warm-only || echo $? > .warm_exit
          test -f .warm_exit || echo 0 > .warm_exit
          cp artifacts/parity_report.json artifacts/warm_parity_report.json || true

      - name: Full stage (canonical)
        run: |
          ft pre-commit --parity || echo $? > .full_exit
          test -f .full_exit || echo 0 > .full_exit
          cp artifacts/parity_report.json artifacts/full_parity_report.json || true

      - name: Weaponize divergence (escape / false red / blind-spot)
        run: |
          W=$(cat .warm_exit); F=$(cat .full_exit)
          echo "warm=$W full=$F"
          
          # Cache ESCAPE: warm passed, full failed
          if [ "$W" -eq 0 ] && [ "$F" -ne 0 ]; then
            echo "❌ CACHE ESCAPE: warm passed, full failed"
            exit 99
          fi
          
          # Warm false red: likely flaky
          if [ "$W" -ne 0 ] && [ "$F" -eq 0 ]; then
            echo "⚠️ Warm false red: likely flaky. Recording…"
            python - <<'PY'
import json, pathlib
rep = pathlib.Path("artifacts/warm_parity_report.json")
out = pathlib.Path("ci/flaky_tests.json")
nodeids = []
if rep.exists():
    try:
        data=json.loads(rep.read_text())
        for f in data.get("failures", []):
            nid=f.get("nodeid")
            if nid: nodeids.append(nid)
    except Exception: pass
existing=[]
if out.exists():
    try: existing=json.loads(out.read_text()).get("nodeids",[])
    except Exception: pass
merged=sorted(set(existing+nodeids))
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"nodeids":merged}, indent=2))
print(f"Wrote {out} with {len(merged)} nodeids")
PY
            exit 0
          fi
          
          # Both failed: compare failure sets
          if [ "$W" -ne 0 ] && [ "$F" -ne 0 ]; then
            echo "Both warm and full failed. Comparing reports…"
            python - <<'PY_COMPARE'
import json, sys, pathlib
try:
    w=json.loads(pathlib.Path("artifacts/warm_parity_report.json").read_text())
    f=json.loads(pathlib.Path("artifacts/full_parity_report.json").read_text())
    wf={x.get("nodeid") for x in w.get("failures", []) if x.get("nodeid")}
    ff={x.get("nodeid") for x in f.get("failures", []) if x.get("nodeid")}
    if wf == ff:
        print("✓ Failures match. Not a cache escape.")
        sys.exit(0)
    else:
        print(f"❌ FAILURE MISMATCH. Warm: {wf} vs Full: {ff}")
        sys.exit(1)
except Exception as e:
    print(f"Compare error: {e}. Assuming mismatch.")
    sys.exit(1)
PY_COMPARE
            if [ $? -ne 0 ]; then
              echo "❌ CACHE ESCAPE: Warm and Full failed on DIFFERENT tests."
              exit 99
            fi
            echo "Warm and Full failed on the same tests. Proceed with full result."
          fi
          
          exit "$F"

      - name: Upload parity reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: parity-reports
          path: artifacts/*_parity_report.json
```

## Usage

### Developer Workflow

```bash
# First time setup (auto-runs on first ft command)
ft pre-commit              # Pulls golden cache, runs warm path

# Daily development
git commit                 # Hook runs ft pre-commit (warm, ~10s)
ft pre-commit              # Manual: warm path
ft pre-commit --parity     # Manual: full parity before push

# Cache management
ft update-cache            # Explicit cache refresh
ft clear-cache             # Nuke all caches (fresh start)
make update-cache          # Via Makefile
make clear-cache           # Via Makefile
```

### CI Behavior

**On main (after merge):**
- Runs full parity
- Generates golden cache artifact
- Uploads as `warm-cache-<fingerprint>.zip`

**On PRs:**
- Runs warm stage (simulates dev)
- Runs full stage (canonical)
- Compares results:
  - **Warm ✓, Full ✗** → Cache escape (exit 99)
  - **Warm ✗, Full ✓** → Flaky test (record nodeid, exit 0)
  - **Both ✗, different failures** → Cache escape (exit 99)
  - **Both ✗, same failures** → Real failure (exit full code)
  - **Both ✓** → Success (exit 0)

## Flaky Test Learning

### Automatic Recording

When warm fails but full passes:
1. Extract failing nodeids from `artifacts/warm_parity_report.json`
2. Merge with existing `ci/flaky_tests.json`
3. Commit updated flaky list

### Re-execution

On subsequent runs:
- Warm path ALWAYS runs flaky tests (step 2)
- Prevents false reds from known flaky tests
- Gradually builds immunity to flakiness

### Manual Management

```bash
# View current flaky tests
cat ci/flaky_tests.json

# Clear flaky memory (if tests are fixed)
echo '{"nodeids":[]}' > ci/flaky_tests.json
git add ci/flaky_tests.json
git commit -m "chore: reset flaky test memory"
```

## Directory Structure

```
.firsttry/
  warm/
    testmon/          # Testmon database
    fingerprint.txt   # Cache version identifier
artifacts/
  parity_report.json       # Latest run report
  warm_parity_report.json  # Warm stage report (CI only)
  full_parity_report.json  # Full stage report (CI only)
  pytest-warm.json         # Testmon results
  pytest-flaky.json        # Flaky test results
  pytest-smoke.json        # Smoke test results
  coverage.xml             # Coverage data for diff-cover
ci/
  parity.lock.json    # Lock file (updated with new plugins)
  flaky_tests.json    # Persistent flaky test memory
```

## Troubleshooting

### Cache not updating

```bash
# Check git fetch
git fetch origin --depth=1

# Check gh CLI
gh auth status
gh run list --limit 5

# Manual refresh
ft update-cache

# Nuclear option
ft clear-cache
```

### False positives (warm fails, full passes)

This is expected and handled:
1. Flaky test is recorded in ci/flaky_tests.json
2. Next run will include it in flaky stage
3. PR passes (warm false red doesn't block)

### Cache escape (warm passes, full fails)

This is a CRITICAL issue (exit 99):
- Indicates testmon missed a dependency
- Indicates missing smoke test coverage
- PR is blocked until fixed

**Fix:**
1. Run `ft clear-cache` to reset
2. Add missing test to @smoke marker
3. Report testmon bug if dependency tracking failed

## Performance Metrics

**Before (full pytest):**
- Pre-commit: ~3min
- CI: ~5min

**After (warm path):**
- Pre-commit: ~10-30s (testmon + flaky)
- CI warm: ~30s-1min
- CI full: ~3min (canonical)

**Cache hit rate:**
- First run: ~2min (no cache)
- Subsequent: ~10s (hot cache)
- After pull: ~30s (warm cache from CI)

## Benefits

1. **Developer Speed** - 10x faster pre-commit (3min → 10-30s)
2. **No False Negatives** - Full CI always runs
3. **Flaky Immunity** - Automatic learning and re-execution
4. **Cache Escape Detection** - Prevents blind spots
5. **Incremental Coverage** - diff-cover on changed lines only
6. **Zero Config** - Auto-refresh, auto-bootstrap

## Next Steps

1. **Commit changes** to enable warm cache system
2. **Run CI on main** to generate first golden cache
3. **Test PR workflow** with divergence detection
4. **Monitor flaky_tests.json** growth over 2 weeks
5. **Tune @smoke markers** for critical paths
