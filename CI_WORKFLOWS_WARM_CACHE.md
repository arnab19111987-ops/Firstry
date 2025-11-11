# CI Workflow Examples for Warm Cache System

## 1. Main Branch - Golden Cache Production

Add to `.github/workflows/ci.yml` (after tests pass):

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
          pip install -e .

      - name: Run full parity
        run: ft pre-commit --parity

      # === GOLDEN CACHE GENERATION (main only) ===
      - name: Compute fingerprint
        if: github.ref == 'refs/heads/main' && success()
        run: |
          mkdir -p .firsttry/warm
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
            -x '*.pyc' -x '.pytest_cache/*' -x '__pycache__/*'

      - name: Upload warm cache artifact
        if: github.ref == 'refs/heads/main' && success()
        uses: actions/upload-artifact@v3
        with:
          name: warm-cache-${{ env.FP }}
          path: artifacts/warm-cache-${{ env.FP }}.zip
          retention-days: 30
```

## 2. PR Workflow - Warm + Full with Divergence Detection

Create `.github/workflows/pr-checks.yml`:

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

      - name: Install gh CLI (for cache download)
        run: |
          type -p curl >/dev/null || sudo apt update && sudo apt install curl -y
          curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
          sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
          echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
          sudo apt update
          sudo apt install gh -y

      - name: Authenticate gh CLI
        run: echo "${{ secrets.GITHUB_TOKEN }}" | gh auth login --with-token

      # === WARM STAGE (simulates developer) ===
      - name: Warm stage - update cache
        run: ft update-cache || true

      - name: Warm stage - run warm path
        continue-on-error: true
        run: |
          ft pre-commit --warm-only || echo $? > .warm_exit
          test -f .warm_exit || echo 0 > .warm_exit

      - name: Warm stage - save report
        run: |
          cp artifacts/parity_report.json artifacts/warm_parity_report.json || true

      # === FULL STAGE (canonical) ===
      - name: Full stage - run full parity
        continue-on-error: true
        run: |
          ft pre-commit --parity || echo $? > .full_exit
          test -f .full_exit || echo 0 > .full_exit

      - name: Full stage - save report
        run: |
          cp artifacts/parity_report.json artifacts/full_parity_report.json || true

      # === DIVERGENCE DETECTION ===
      - name: Detect cache escape and learn flaky tests
        run: |
          W=$(cat .warm_exit)
          F=$(cat .full_exit)
          echo "📊 Results: warm=$W full=$F"
          
          # Case 1: Cache ESCAPE (warm ✓, full ✗)
          if [ "$W" -eq 0 ] && [ "$F" -ne 0 ]; then
            echo "❌ CACHE ESCAPE DETECTED"
            echo "Warm path passed but full parity failed."
            echo "This indicates:"
            echo "  - testmon missed a dependency, OR"
            echo "  - missing @smoke test coverage"
            echo ""
            echo "Action required: Fix the gap in warm path coverage"
            exit 99
          fi
          
          # Case 2: Warm false red (warm ✗, full ✓) → Flaky test
          if [ "$W" -ne 0 ] && [ "$F" -eq 0 ]; then
            echo "⚠️  FLAKY TEST DETECTED"
            echo "Warm path failed but full parity passed."
            echo "Recording flaky test(s) for future runs..."
            
            python - <<'PY'
import json
import pathlib

# Load warm failures
rep = pathlib.Path("artifacts/warm_parity_report.json")
nodeids = []
if rep.exists():
    try:
        data = json.loads(rep.read_text())
        for f in data.get("failures", []):
            nid = f.get("nodeid")
            if nid:
                nodeids.append(nid)
                print(f"  - {nid}")
    except Exception as e:
        print(f"Failed to parse warm report: {e}")

# Load existing flaky tests
out = pathlib.Path("ci/flaky_tests.json")
existing = []
if out.exists():
    try:
        existing = json.loads(out.read_text()).get("nodeids", [])
    except Exception:
        pass

# Merge and save
merged = sorted(set(existing + nodeids))
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"nodeids": merged}, indent=2))
print(f"\n✓ Updated {out} with {len(merged)} total flaky tests")
PY
            
            # Commit flaky tests (if any new ones)
            if [ -f ci/flaky_tests.json ]; then
              git config --global user.name "github-actions[bot]"
              git config --global user.email "github-actions[bot]@users.noreply.github.com"
              git add ci/flaky_tests.json
              git diff --cached --quiet || git commit -m "chore: update flaky test list [skip ci]"
              git push origin HEAD:${{ github.head_ref }} || echo "Push failed (may need permissions)"
            fi
            
            echo "✓ Flaky test recorded. Allowing PR to pass."
            exit 0
          fi
          
          # Case 3: Both failed → Compare failure sets
          if [ "$W" -ne 0 ] && [ "$F" -ne 0 ]; then
            echo "⚠️  Both warm and full failed"
            echo "Comparing failure sets to detect cache escapes..."
            
            python - <<'PY_COMPARE'
import json
import sys
import pathlib

try:
    # Load reports
    w = json.loads(pathlib.Path("artifacts/warm_parity_report.json").read_text())
    f = json.loads(pathlib.Path("artifacts/full_parity_report.json").read_text())
    
    # Extract failure nodeids
    wf = {x.get("nodeid") for x in w.get("failures", []) if x.get("nodeid")}
    ff = {x.get("nodeid") for x in f.get("failures", []) if x.get("nodeid")}
    
    print(f"Warm failures: {len(wf)} tests")
    print(f"Full failures: {len(ff)} tests")
    
    if wf == ff:
        print("\n✓ Failure sets match - consistent results")
        print("This is a real failure, not a cache issue.")
        sys.exit(0)
    else:
        print(f"\n❌ CACHE ESCAPE: Different failure sets detected")
        print(f"\nWarm-only failures: {wf - ff}")
        print(f"Full-only failures: {ff - wf}")
        sys.exit(1)
        
except Exception as e:
    print(f"⚠️  Error comparing reports: {e}")
    print("Assuming cache escape to be safe")
    sys.exit(1)
PY_COMPARE
            
            if [ $? -ne 0 ]; then
              echo ""
              echo "❌ CACHE ESCAPE: Warm and full failed on DIFFERENT tests"
              exit 99
            fi
            
            echo ""
            echo "Same tests failed in both warm and full."
            echo "Proceeding with full parity result."
          fi
          
          # Case 4: Both passed
          if [ "$W" -eq 0 ] && [ "$F" -eq 0 ]; then
            echo "✅ SUCCESS: Both warm and full passed"
          fi
          
          exit "$F"

      - name: Upload parity reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: parity-reports-${{ github.run_id }}
          path: |
            artifacts/warm_parity_report.json
            artifacts/full_parity_report.json
            ci/flaky_tests.json
```

## 3. Optional: Nightly Flaky Test Audit

Create `.github/workflows/flaky-audit.yml`:

```yaml
name: Flaky Test Audit

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Audit flaky tests
        run: |
          if [ -f ci/flaky_tests.json ]; then
            count=$(jq '.nodeids | length' ci/flaky_tests.json)
            echo "📊 Flaky Test Count: $count"
            
            if [ "$count" -gt 50 ]; then
              echo "⚠️  WARNING: More than 50 flaky tests detected"
              echo "Consider investigating and fixing high-frequency flaky tests"
            fi
            
            echo "Flaky tests:"
            jq -r '.nodeids[]' ci/flaky_tests.json
          else
            echo "✓ No flaky tests recorded"
          fi

      - name: Post to Slack (optional)
        if: env.SLACK_WEBHOOK_URL
        run: |
          # Add Slack notification here
          echo "Flaky test report posted to Slack"
```

## 4. Pre-commit Hook (Local)

In `.githooks/pre-commit`:

```bash
#!/bin/bash
# Local pre-commit hook - runs warm path

set -e

echo "[pre-commit] Running FirstTry warm path..."

# Run warm path (fast, ~10-30s)
ft pre-commit --warm-only --explain

echo "[pre-commit] ✓ Warm path passed"
```

## Environment Variables

Set these in GitHub Settings → Secrets:

- `GITHUB_TOKEN` - Already available (for gh CLI)
- `SLACK_WEBHOOK_URL` - Optional (for flaky test notifications)

## Permissions

Ensure GitHub Actions has write permissions for committing flaky test updates:

In `.github/workflows/pr-checks.yml`, add:

```yaml
permissions:
  contents: write
  pull-requests: write
```

## Testing the Workflow

1. **Create test PR:**
   ```bash
   git checkout -b test-warm-cache
   # Make a small change
   echo "# test" >> README.md
   git add README.md
   git commit -m "test: warm cache workflow"
   git push origin test-warm-cache
   ```

2. **Check Actions tab:**
   - Warm stage should complete in ~30s
   - Full stage should complete in ~3min
   - Divergence detection should pass

3. **Test cache escape:**
   - Make a change that breaks a test
   - Comment out test in affected tests
   - Warm should pass (testmon skips), full should fail
   - Should see exit 99 and PR blocked

4. **Test flaky detection:**
   - Introduce a random.choice() test failure
   - Warm may fail (50% chance)
   - Full should pass
   - Check ci/flaky_tests.json for new entry

## Monitoring

Check these after 2 weeks:

```bash
# Flaky test growth
git log --oneline ci/flaky_tests.json

# Cache escape frequency
gh run list --workflow=pr-checks.yml --json conclusion,name | \
  jq '.[] | select(.conclusion == "failure")'

# Cache hit rate
# Look at warm stage duration in Actions
```

## Troubleshooting

**Warm stage times out:**
- Check testmon database size: `du -sh .firsttry/warm/testmon`
- Clear if > 100MB: `ft clear-cache`

**Cache never downloads:**
- Verify gh CLI: `gh auth status`
- Check artifact exists: `gh run list --limit 1`
- Check retention: Artifacts expire after 30 days

**Flaky tests growing:**
- Audit top flaky tests: `jq '.nodeids' ci/flaky_tests.json`
- Fix or mark with pytest.mark.flaky
- Reset list: `echo '{"nodeids":[]}' > ci/flaky_tests.json`

**Cache escape every PR:**
- Review @smoke marker coverage
- Check testmon dependency tracking
- May need to tune testmon configuration
