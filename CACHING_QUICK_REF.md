# Caching Quick Reference

## Performance at a Glance

```
Cold run:     3.1s   ████████████████████████████████ (baseline)
Warm run:     2.1s   ████████████████████░░░░░░░░░░░░ (1.5x faster)
Zero-run:    0.005s  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ (620x faster!)
```

## Two-Level Caching

### 1. Zero-Run Cache (Whole Repository)
- **Check**: Repo fingerprint unchanged?
- **Result**: Return cached report in ~5ms
- **Triggers**: All tasks passed last run + no file changes

### 2. Per-Task Cache (Individual Tools)
- **Check**: Task inputs unchanged?
- **Result**: Skip subprocess, return cached result in ~1ms
- **Triggers**: Task-specific files unchanged + task passed before

## CLI Usage

```bash
# Standard (auto-cached)
firsttry run

# Force real run (disable zero-run cache)
firsttry run --no-verify-fastpath

# Verify-only (fail if cache miss)
firsttry run --verify-only

# Clear cache
rm -rf .firsttry/cache
```

## Cache Status in Output

```
[cli] ✓ Zero-run cache hit (fingerprint=a3f2c4b1...)
[executor] Cache hit ruff: ruff check src
[executor] Cache hit mypy: mypy src
[executor] Running pytest: pytest -q
```

## report.json Evidence

```json
{
  "verified_from_cache": true,     // Zero-run cache hit
  "tasks": [
    {
      "id": "ruff",
      "code": 0,
      "cache": "hit",               // Per-task cache hit
      "duration_s": 0.000           // Millisecond timing
    }
  ]
}
```

## Cache Invalidation

**Zero-run cache** invalidates on:
- Any file change in src/, tests/, config files
- Python/tool version changes
- Previous run had failures

**Per-task cache** invalidates on:
- ruff: Changes to `src/`
- mypy: Changes to `src/` or `pyproject.toml`
- pytest: Changes to `src/`, `tests/`, or `pyproject.toml`

## Files

```
Created:
  src/firsttry/runner/state.py        # Repo fingerprinting
  src/firsttry/runner/taskcache.py    # Per-task caching

Modified:
  src/firsttry/runner/executor.py     # Integrated caching
  src/firsttry/cli_dag.py              # Zero-run fast-path

Storage:
  .firsttry/cache/last_green_run.json # Repo-level cache
  .firsttry/cache/tasks/              # Per-task results
```

## Benchmarks

```bash
# Run performance verification
bash tools/verify_perf.sh

# Expected output:
Cold:     3.1s  (no cache)
Warm:     2.1s  (task cache: ruff+mypy cached)
Zero-run: 0.005s (full cache: nothing executed)
```

## How It Works

### Zero-Run Fast-Path
```
1. Compute repo fingerprint (BLAKE2b of all files)
2. Load last green run from cache
3. If fingerprints match:
   → Return cached report (~5ms)
4. Else:
   → Proceed with normal execution
   → Save state if all tasks pass
```

### Per-Task Cache
```
1. Compute cache key (cmd + inputs + salt)
2. Check task cache
3. If hit:
   → Return cached result (~1ms)
4. Else:
   → Run subprocess normally
   → Cache result if exit code 0
```

## Performance Guarantees

✅ Zero-run cache hit: **< 10ms**  
✅ Task cache hit: **< 5ms**  
✅ No false positives: **BLAKE2b guarantees**  
✅ Self-documenting: **Cache status in report.json**  

## Implementation Status

✅ Priority A: Zero-run verification cache  
✅ Priority B: Per-task caching  
⏳ Priority C: Sub-second optimizations (optional)

---

**Result**: Millisecond performance when nothing changed!
