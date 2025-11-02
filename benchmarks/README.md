# FirstTry Benchmark Suite

This benchmark suite answers the 5 critical performance questions for FirstTry:

1. **Startup cost**: "How long does `firsttry --help` and detection take?"
2. **Cold run**: "How bad is a first run on a new repo?"
3. **Warm run**: "Does the cache + --changed-only actually help?"
4. **Profile/tier cost**: "How much slower is `--profile strict` vs `--profile fast` / `--tier teams`?"
5. **CI parity cost**: "How much extra time does `--source ci` add to a run?"

## Usage

```bash
# Run full benchmark suite
make bench

# Run shortened benchmark (future feature)
make bench-short

# Manual run
python benchmarks/bench_runner.py
```

## Test Fixtures

- **repo-a-no-config**: Small repo (200-500 files), no configuration
- **repo-b-ci-only**: Has CI workflows, tests + linter config
- **repo-c-team-config**: Has CI + firsttry.toml, multiple stacks
- **repo-d-monorepo**: Large repo (10k+ files) for stress testing

## Metrics Collected

For each command run:
- `cmd` - exact command executed
- `total_time_sec` - wall-clock time (float, seconds)
- `exit_code` - 0 or nonzero
- `phase_breakdown` - timing phases if FirstTry prints them
- `cpu_count` - from the host
- `repo_size_files` - number of files in repo
- `cache_state` - "cold" | "warm" | "changed-only"
- `profile/tier` - "fast" | "strict" | "developer" | "teams"
- `firsttry_version` - from firsttry --version
- `environment` - "devcontainer" | "codespace" | "local"
- `license_state` - "not-required" | "trial" | "locked"

## Pass/Fail Rules

### Startup (help/version)
- ✅ PASS: <= 0.5s
- ⚠️ WARN: 0.5–1.0s  
- ❌ FAIL: > 1.0s

### Cold detect run (small repo)
- ✅ PASS: <= 30s
- ⚠️ WARN: 30–45s
- ❌ FAIL: > 45s

### Warm detect run
- ✅ PASS: at least 30% faster than cold
- ❌ FAIL: speedup < 30% → cache not working

### Changed-only run
- ✅ PASS: <= 30s
- ❌ FAIL: > 30s → biggest speed feature must be fast

### Strict/profile-heavy
- ✅ PASS: <= 90s
- ❌ FAIL: > 120s → too heavy for local use

### CI source run
- ✅ PASS: fails/passes for same reason as CI
- ❌ FAIL: diverges from CI → parity broken

## Results

Results are stored in `benchmarks/results/` as timestamped JSON files for comparison across runs and versions.