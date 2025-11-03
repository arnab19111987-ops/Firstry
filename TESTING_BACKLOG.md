# Testing & Quality Backlog

Bite-sized improvements to maintain and enhance the test suite.

## Priority Tasks

### [CLI] Convert Remaining Skipped CLI Tests
**Status**: 4/23 completed ✅  
**Effort**: ~15 minutes per test

Pattern established in `tests/test_cli_doctor_and_license.py`.

**Completed conversions** (4):
- ✅ `test_cli_doctor_uses_report`
- ✅ `test_cli_doctor_exitcode_nonzero`
- ✅ `test_cli_license_verify_prints_status`
- ✅ `test_cli_license_verify_nonvalid_exitcode`

Remaining skipped tests to convert (~19):
- `test_cli_install_hooks.py` (1 test)
- Other CLI test files with argparse skips

**How to convert**:
```python
# Old (skipped):
@pytest.mark.skip(reason="CLI changed from Click to argparse")
def test_something():
    from click.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(main, ["command"])
    assert result.exit_code == 0

# New (working):
def test_something():
    from tests.cli_utils import run_cli
    code, out, err = run_cli(["command"])
    assert code == 0
    assert "expected output" in out
```

### [Gates] Move _safe_gate to gates/utils.py
**Status**: ✅ Completed  
**Effort**: 10 minutes

Refactored `_safe_gate()` to `src/firsttry/gates/utils.py` for better code organization.

**Changes**:
- ✅ Created `src/firsttry/gates/utils.py` with `_safe_gate()` function
- ✅ Updated `src/firsttry/gates/__init__.py` to import from utils
- ✅ All tests passing with new structure

**Benefits**:
- ✅ Cleaner separation of concerns
- ✅ Easier to test `_safe_gate` in isolation  
- ✅ Makes `__init__.py` more readable

### [Report] Use Display Tier Names
**Status**: Not started  
**Effort**: 20 minutes

The new license system has display names ("Free Lite", "Free Strict", "Pro", "ProMax") but some reports still show raw tier IDs ("free-lite", "developer").

**Files to update**:
- `src/firsttry/doctor.py` - Report rendering
- `src/firsttry/cli.py` - Status command output
- Look for: `tier_map.get_display_name(tier)` usage

**Test**: Run `firsttry status` and verify output shows "Free Lite" not "free-lite"

### [Coverage] Improve Coverage Reporting
**Status**: ✅ pytest-cov installed and working  
**Effort**: 5 minutes

**Current coverage**: 8.2% (on benchmark tests)  
**Target**: 25-30% (achievable with existing tests)

**Actions**:
- ✅ Installed pytest-cov
- ✅ Updated `.coveragerc` to omit legacy/docker/vscode modules
- ✅ Verified coverage reporting works: `pytest tests --cov=src/firsttry --cov-report=term --cov-report=json:coverage.json`
- ✅ `coverage.json` parsing confirmed working

**Next**: Run full suite with coverage to identify low-hanging fruit for unit tests.

### [CI] Add Gate Regression Prevention
**Status**: ✅ Completed  
**Effort**: 15 minutes

Created GitHub Actions workflow for critical gates and CLI tests.

**File**: `.github/workflows/gates-safety-suite.yml`

**What it does**:
- ✅ Runs critical gate tests on every push/PR
- ✅ Runs CLI argparse compatibility tests
- ✅ Includes optional coverage reporting job
- ✅ Tests protected:
  - `tests/test_gates_core.py`
  - `tests/test_gates_comprehensive.py`
  - `tests/test_gates_pytest_rich_output.py`
  - `tests/test_cli_doctor_and_license.py`

**Why**: The `test_gate_runner_handles_exception` bug was subtle - this ensures it can't regress silently.

## Future Enhancements

### [Gates] Optional: Parser Support in _safe_gate
**Status**: Deferred (check_tests works as-is)  
**Effort**: 30 minutes

If we need more rich-output gates (like check_tests), consider enhancing `_safe_gate`:

```python
def _safe_gate(gate_id, cmd, *, parser=None, ok_if_missing=True):
    ...
    if proc.returncode == 0 and parser is not None:
        parsed = parser(proc.stdout, proc.stderr)
        return GateResult(..., details=parsed)
```

Then gates can stay simple while providing rich output:
```python
def check_tests():
    return _safe_gate("tests", ["pytest", "-q"], parser=_parse_pytest_output)
```

**Benefit**: DRY - exception handling in one place, custom parsing per gate.

### [Testing] Add Unit Tests for Pure Functions
**Status**: Not started  
**Effort**: 2-3 hours

Target modules with pure functions (easy to test, high coverage gain):
- `firsttry.license_guard.normalize_tier`
- `firsttry.change_detector.categorize_changed_files`
- `firsttry.profiler.get_profiler`
- `firsttry.config_loader.merge_configs`

**Impact**: Could lift coverage from 18% → 30% with 10-15 unit tests.

## Completed ✅

- ✅ Fix `test_gate_runner_handles_exception` - Added `_safe_gate()` helper
- ✅ Create `tests/cli_utils.py` for argparse testing
- ✅ Convert 4 CLI tests as proof of concept
- ✅ Add regression test `test_gates_pytest_rich_output.py` (2 tests)
- ✅ Update `.coveragerc` to omit legacy/docker/vscode modules
- ✅ Add protective comment above `check_tests()` implementation
- ✅ Move `_safe_gate()` to `src/firsttry/gates/utils.py`
- ✅ Install pytest-cov and verify coverage reporting works
- ✅ Create GitHub Actions workflow `.github/workflows/gates-safety-suite.yml`
