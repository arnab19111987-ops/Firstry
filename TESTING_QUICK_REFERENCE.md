# Quick Reference - Coverage & Testing

## Current Status
✅ Coverage: **25.1%** (meets critical floor 18%, warning floor 20%)  
✅ Tests: **223 passing, 20 skipped, 0 failing**  
✅ CI: Coverage floor monitoring active  

## Common Commands

### Run tests with coverage
```bash
make coverage-check
```

### Run full test suite
```bash
pytest tests -v
```

### Run critical CI tests only (fast)
```bash
pytest \
  tests/test_gates_core.py \
  tests/test_gates_comprehensive.py \
  tests/test_gates_pytest_rich_output.py \
  tests/test_cli_doctor_and_license.py \
  tests/test_cli_routing.py \
  tests/test_cli_install_hooks.py \
  tests/test_reports_tier_display.py \
  tests/test_pure_functions.py \
  tests/test_reporting.py \
  -v
```

### Check coverage percentage
```bash
python -c "import json; d=json.load(open('coverage.json')); print(f\"Coverage: {d['totals']['percent_covered']:.1f}%\")"
```

### Validate coverage floor
```bash
./scripts/check_coverage_floor.sh
```

## Coverage Thresholds

| Level | Percentage | Action |
|-------|------------|--------|
| Critical Floor | 18% | Hard CI failure |
| Warning Floor | 20% | Soft warning |
| Current | 25.1% | ✅ Healthy |
| Target | 27% | Optional stretch goal |

## Test Files by Purpose

### Gate Tests (Core Safety)
- `test_gates_core.py` - Gate exception handling, _safe_gate() helper
- `test_gates_comprehensive.py` - All gate implementations
- `test_gates_pytest_rich_output.py` - Rich output parsing (pytest test counts)

### CLI Tests (Argparse Migration)
- `test_cli_doctor_and_license.py` - doctor/license commands
- `test_cli_routing.py` - Command routing, help, version
- `test_cli_install_hooks.py` - setup command

### Coverage Boost Tests
- `test_reports_tier_display.py` - Tier metadata and classification
- `test_pure_functions.py` - Pure functions in repo_rules, change_detector
- `test_license_guard_mapping.py` - License tier mappings
- `test_context_builders.py` - Repository context building
- `test_cache_fastpaths.py` - Cache operations

### Reporting Tests
- `test_reporting.py` - Report schema validation, CLI error handling

## Files Modified in Coverage Boost

### Bug Fixes
- `src/firsttry/cache.py` - Added defensive check for missing "repos" key

### CI/CD
- `.github/workflows/gates-safety-suite.yml` - Added 5 new critical test files
- `scripts/check_coverage_floor.sh` - Coverage validation script (NEW)
- `Makefile` - Added `coverage-check` target

### Test Infrastructure
- `tests/cli_utils.py` - CLI testing utility for argparse (NEW)

### New Test Files (7 files, 37 tests)
1. `tests/test_cli_routing.py` (9 tests)
2. `tests/test_license_guard_mapping.py` (3 tests)
3. `tests/test_context_builders.py` (5 tests)
4. `tests/test_cache_fastpaths.py` (4 tests)
5. `tests/test_cli_install_hooks.py` (1 test)
6. `tests/test_reports_tier_display.py` (8 tests)
7. `tests/test_pure_functions.py` (7 tests)

## High-Impact Modules

Top 5 by coverage improvement potential:

| Module | Current Coverage | Potential |
|--------|------------------|-----------|
| `lazy_orchestrator.py` | 0% | High (66 stmts) |
| `cli_run_profile.py` | 0% | Medium (51 stmts) |
| `runners/python.py` | 18.3% | Medium (92 stmts) |
| `ci_parser.py` | 41.2% | Medium (196 stmts) |
| `cli.py` | 46.2% | Medium (344 stmts) |

## Skipped Tests Available for Conversion

10 tests skipped due to "CLI changed from Click to argparse":
- Ready to convert using `cli_utils.run_cli()` pattern
- Each conversion adds ~0.2-0.3% coverage
- Combined potential: ~2-3% coverage gain

## Quick Debug

### If tests fail:
```bash
# Run with full traceback
pytest tests/test_name.py -v --tb=long

# Run single test
pytest tests/test_name.py::test_function_name -v
```

### If coverage drops:
```bash
# Check what's missing coverage
pytest tests --cov=src/firsttry --cov-report=term-missing

# Generate HTML report
pytest tests --cov=src/firsttry --cov-report=html
open htmlcov/index.html
```

## CI Workflow

GitHub Actions runs on every push/PR to main/develop:
1. **Gate & CLI Safety Suite** - 56 critical tests
2. **Coverage Check** - Full test suite with floor validation
3. **Artifact Upload** - coverage.json for historical tracking

View in: `.github/workflows/gates-safety-suite.yml`
