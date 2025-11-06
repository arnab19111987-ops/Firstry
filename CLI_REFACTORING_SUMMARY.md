# CLI Refactoring Patch – Complete Summary

## What Was Applied

### 1. **Shared Flag Builder Function (`_add_run_flags`)**
   - **Location:** `src/firsttry/cli.py` (lines 149-193)
   - **Purpose:** De-drifts CLI arguments across all entry points
   - **Flags Added:**
     - `--profile` – Named profile (e.g., 'fast', 'ci')
     - `--level` – Gate level (e.g., 'lite', 'strict')
     - `--tier` – Product tier (e.g., 'free-lite', 'pro')
     - `--report-json` – JSON report output path
     - `--report-schema` – Print schema and exit
     - `--dry-run` – Plan without execution
     - `--debug-report` – Debug report helper
   - **Benefit:** Single source of truth prevents flag regressions

### 2. **Enhanced `cmd_run()` Function**
   - **Location:** `src/firsttry/cli.py` (lines 552-619)
   - **Improvements:**
     - Now uses `_add_run_flags()` for consistency
     - Cleaner positional argument handling (optional legacy "mode")
     - Type annotation: `argv: Optional[list[str]] = None`
     - Fast path for `--report-schema` flag
     - Better docstring
   - **Backward Compatible:** Supports legacy `firsttry run strict` calls

### 3. **Minimal Parity Test Suite**
   - **Location:** `tests/test_cli_args_parity_min.py` (new file)
   - **15 Fast Tests:**
     - Parametrized flag acceptance tests (no tool execution)
     - Mock-based orchestrator tests
     - Help text validation
     - `_add_run_flags` function export test
   - **Speed:** ~0.08s (vs full integration tests)
   - **Purpose:** Quick regression detection during development

## Test Results

### ✅ All Checks Pass
```
CLI Args Parity (full):  6/6 ✓
CLI Args Parity (min):   15/15 ✓
FirstTry strict:         3/3 ✓ (ruff, pytest, mypy)
Pre-commit hook:         All cached ✓
Ruff:                    All checks passed ✓
Mypy:                    No issues found (260 files) ✓
```

## Key Benefits

1. **Prevention of CLI Regressions**
   - Shared flag builder prevents drift
   - Dual test suite (fast + integration)
   - Parity tests in pre-commit hook

2. **Faster Development**
   - Minimal tests run in ~0.08s (vs 10+ seconds for full suite)
   - Mocked orchestrator = no tool execution in unit tests
   - Easy to add new flags to both tests

3. **Better Maintainability**
   - Single definition of CLI flags
   - Clear separation: flag parsing vs. execution
   - Type hints on `cmd_run()` signature

## Files Changed

1. **src/firsttry/cli.py**
   - Added `_add_run_flags(p: argparse.ArgumentParser)` 
   - Refactored `cmd_run()` to use shared flags
   - Type improvements (Optional, etc.)

2. **tests/test_cli_args_parity_min.py** (NEW)
   - 15 parametrized and focused tests
   - Fast flag parity + mock-based integration
   - No actual tool execution

3. **requirements-dev.txt**
   - Added `sqlalchemy>=1.4.0`
   - Added `anyio>=3.0`

4. **tests/test_db_sqlite.py**
   - Added `pytest.importorskip("sqlalchemy", ...)`
   - Gracefully skips when SQLAlchemy unavailable

5. **tools/ft_vs_manual_collate.py**
   - Fixed E702 violations (multi-statement lines with semicolons)

6. **mypy.ini**
   - Refined exclude patterns for demo/script files

## How to Use

### Run All Parity Tests (Fast)
```bash
python -m pytest tests/test_cli_args_parity_min.py -v
```

### Run Integration Tests
```bash
python -m pytest tests/test_cli_args_parity.py -v
```

### Test New Flag
1. Add flag to `_add_run_flags()` 
2. Add parametrized test case to `test_cli_args_parity_min.py`
3. Run tests: `pytest tests/test_cli_args_parity_min.py -v`

### Extend `cmd_run()` Behavior
```python
def cmd_run(argv: Optional[list[str]] = None) -> int:
    # ... existing code ...
    ns = parser.parse_args(argv)
    
    # Your new flag logic here
    if ns.your_new_flag:
        # do something
        pass
```

## CI Integration

The pre-commit hook already validates this:
```bash
.git/hooks/pre-commit
  → CLI args parity probe (syntax check)
  → FirstTry lite run (functional check)
```

## Next Steps (Optional)

1. **Install optional dev dependencies** (for CI environments):
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Add CI job** to run parity tests:
   ```yaml
   - name: CLI Parity Tests
     run: pytest tests/test_cli_args_parity_min.py -v
   ```

3. **Monitor** for any new CLI flag proposals:
   - Update `_add_run_flags()` 
   - Add test cases
   - Run full suite

## Verification Checklist

- [x] All parity tests pass (21/21)
- [x] FirstTry strict mode works (3/3 checks)
- [x] Pre-commit hook passes
- [x] Ruff: All checks passed
- [x] Mypy: No issues (260 files)
- [x] Type hints improved
- [x] Backward compatibility maintained
- [x] Documentation clear in docstrings
