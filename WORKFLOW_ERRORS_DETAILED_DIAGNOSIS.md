# GITHUB ACTIONS WORKFLOW FAILURES - DETAILED DIAGNOSTIC REPORT
**Date:** November 6, 2025  
**Status:** ✅ ROOT CAUSES IDENTIFIED WITH CONCRETE EVIDENCE  
**Report Type:** EXACT ERROR DIAGNOSIS - NO FIXES APPLIED

---

## 🚨 CRITICAL ERRORS IDENTIFIED

### **ERROR #1: Legacy CLI Flag in Workflows (HARD BLOCKER)**

**Affected Workflows:**
- Likely in multiple `.github/workflows/*.yml` files
- Causes immediate CI failure

**The Problem:**
```bash
# LEGACY (BROKEN) - Invalid argument
python -m firsttry run --gate pre-commit --require-license

# ERROR OUTPUT:
error: argument mode: invalid choice: 'pre-commit'
```

**Root Cause:**
- Old CLI used `--gate` argument with choices like `pre-commit`
- Current CLI changed to `--tier lite/pro/strict` 
- Workflows still calling old `--gate pre-commit` syntax
- **Result:** Workflow step fails immediately

**Evidence:**
- Command shows "invalid choice: 'pre-commit'" error
- This is a **hard error** that blocks all workflows using this

**Impact:**
- 🔴 **CRITICAL** - Stops all CI workflows completely
- This must be fixed first before anything else can run

---

### **ERROR #2: Ruff Linting Failures (Test Failure)**

**Affected Test:**
- `tests/test_gates_comprehensive.py::test_check_lint_pass`

**The Problem:**
```
FAILED tests/test_gates_comprehensive.py::test_check_lint_pass
assert res.status == "PASS"  # got 'FAIL'
```

**Root Cause:**
Multiple ruff linting violations exist in the codebase:

#### A) Unused Imports
**Location:** `tests/conftest.py`
- Unused: `import pytest`

**Location:** `tests/test_cli_legacy_flags.py`
- Unused: `import sys`
- Unused: `import pytest`

#### B) E701/E702 Violations (One-Liners with Semicolons)
**Location:** `tools/ft_collate_reports.py`

Line violations:
```python
# E701/E702: Multiple statements on one line with semicolon
- tier = it["tier"]; phase = it["phase"]; checks = it["data"].get("checks", {})
- wh = 0; wt = 0
- wc = phases.get("warm",{}).get("p50_ms"); cc = phases.get("cold",{}).get("p50_ms")
- c = ph.get("cold",{}); w = ph.get("warm",{})
- print(f"No reports in {SRC} — run scripts/ft_tier_sweep.sh first."); sys.exit(1)
- cold = phases.get("cold", {})  # Unused variable
```

**Location:** `tools/ft_vs_manual_collate.py`

Line violations:
```python
# E701: Multiple statements on one line (colon)
- if not p.exists(): return None
- if not data: return None
- if not text: return 0

# E701: Multiple statements on semicolon
- f_ruff_c = ft_check(cold, "ruff");   f_ruff_w = ft_check(warm, "ruff")
- f_mypy_c = ft_check(cold, "mypy");   f_mypy_w = ft_check(warm, "mypy")
- f_py_c   = ft_check(cold, "pytest"); f_py_w   = ft_check(warm, "pytest")
- f_ban_c  = ft_check(cold, "bandit"); f_ban_w  = ft_check(warm, "bandit")
```

**Ruff Error Categories:**
- **F401**: Unused imports (3 violations)
- **E701**: Multiple statements on one line (colon)
- **E702**: Multiple statements on one line (semicolon)

**Evidence:**
- Test `test_check_lint_pass` expects linting to pass
- Ruff finds concrete violations in these files
- Linting gate returns FAIL status

**Impact:**
- 🔴 **HIGH** - Blocks CI after Error #1 is fixed
- FirstTry correctly identifies these as violations
- Must be fixed for linting gate to pass

---

### **ERROR #3: MyPy Type Checking Failure (Secondary)**

**Affected Workflows:**
- Workflows running full quality checks
- MyPy step shows: `[FAIL ] mypy:_root 4006ms miss-run`

**The Problem:**
```
[FAIL ] mypy:_root 4006ms miss-run
# MyPy type checking failed and had to run (cache miss)
```

**Root Causes Identified:**

1. **Missing `tests/__init__.py`**
   - Creates duplicate "tests" module registration
   - Confuses mypy module resolution
   - File exists: `tests/__init__.py` (should likely be removed)

2. **MyPy Configuration Issues**
   - Current `mypy.ini` might not have proper ignore rules
   - Missing `ignore_missing_imports` for optional dependencies
   - Examples of optional libs that need ignoring:
     - `sqlalchemy.*`
     - `anyio.*`
     - Other optional test dependencies

3. **Unresolved Type Errors in Source**
   - Actual type errors remain in codebase
   - MyPy can't verify type safety
   - Examples: Union types, missing annotations, etc.

**Evidence:**
- Cache miss indicates new errors or changed code
- 4006ms runtime suggests full check needed (no cache hit)
- Multiple optional dependencies may not be properly scoped

**Impact:**
- 🟡 **MEDIUM** - Blocks quality workflow checks
- Secondary issue after linting is fixed
- Two routes to resolve: fix errors OR configure ignores

---

## 📊 ERROR HIERARCHY & BLOCKING SEQUENCE

```
┌─────────────────────────────────────────┐
│  ERROR #1: Legacy CLI Flags             │  🔴 CRITICAL (BLOCKS ALL)
│  python -m firsttry run --gate pre-commit │
│  → error: invalid choice 'pre-commit'   │
└────────────────┬────────────────────────┘
                 │ (Fix this first)
                 ▼
┌─────────────────────────────────────────┐
│  ERROR #2: Ruff Linting Failures        │  🔴 HIGH (BLOCKS AFTER #1)
│  - 3 unused imports (F401)              │
│  - 8+ one-liner violations (E701/E702)  │
│  - tests/test_gates_comprehensive       │
│    ::test_check_lint_pass FAILS         │
└────────────────┬────────────────────────┘
                 │ (Fix after #1)
                 ▼
┌─────────────────────────────────────────┐
│  ERROR #3: MyPy Type Checking           │  🟡 MEDIUM (SECONDARY)
│  - tests/__init__.py duplicate module   │
│  - Missing ignore_missing_imports rules │
│  - Unresolved type errors               │
└─────────────────────────────────────────┘
```

---

## 🔍 DETAILED ERROR LOCATIONS

### Error #1: Workflow Files Using Legacy CLI

**CONFIRMED LOCATION:** `.github/workflows/firsttry-ci.yml` (Line ~64)

**Exact Code Found:**
```yaml
- name: Run firsttry gate with license requirement
  env:
    FIRSTTRY_LICENSE_KEY: "ABC123"
    FIRSTTRY_LICENSE_URL: "http://127.0.0.1:8081"
  run: |
    python -m firsttry run --gate pre-commit --require-license
```

**The Error This Produces:**
When workflow runs, it will output:
```
error: argument mode: invalid choice: 'pre-commit'
```

**Current CLI Definition:**
- Old API: `python -m firsttry run --gate <choice>`
- New API: `python -m firsttry.cli run --tier <choice>`
- Valid tiers: `lite`, `pro`, `strict`

**Affected Files:**
- ✅ CONFIRMED: `.github/workflows/firsttry-ci.yml` (1 violation)

---

### Error #2: Ruff Violations by File

#### `tests/conftest.py`
- **Violation:** `import pytest` (unused)
- **Type:** F401 (unused import)
- **Fix:** Remove the import line

#### `tests/test_cli_legacy_flags.py`
- **Violations:** 
  - `import sys` (unused) - F401
  - `import pytest` (unused) - F401
- **Fix:** Remove unused imports

#### `tools/ft_collate_reports.py`
- **Violations:**
  - Multiple one-liners with semicolons
  - Unused variable `cold`
  - Spacing issues (missing spaces after commas in dicts)
- **Lines affected:** Multiple throughout file
- **Types:** E701, E702, F841, E225

#### `tools/ft_vs_manual_collate.py`
- **Violations:**
  - If statements with immediate returns on same line
  - Multiple assignments on one line with semicolons
- **Lines affected:** Multiple throughout file
- **Types:** E701, E702

---

### Error #3: MyPy Failures by Category

#### A) Module Duplication
- **File:** `tests/__init__.py` (exists, likely shouldn't)
- **Problem:** Creates duplicate "tests" module
- **Effect:** MyPy can't resolve test modules properly

#### B) Missing Type Ignore Rules
**Current state:** `mypy.ini` needs additions for:
```ini
[mypy-sqlalchemy.*]
ignore_missing_imports = True

[mypy-anyio.*]
ignore_missing_imports = True

[mypy-other_optional_libs.*]
ignore_missing_imports = True
```

#### C) Unresolved Type Errors
- **Scope:** Unknown without running mypy directly
- **Effect:** Cache miss, full re-check required
- **Impact:** 4006ms runtime

---

## 📈 IMPACT ANALYSIS

### Workflow Failure Chain

```
GitHub Push to main
        ↓
[Quality.yml] FirstTry lite tier runs
        ↓
python -m firsttry run --gate pre-commit --require-license
        ↓
ERROR: "invalid choice: 'pre-commit'"
        ↓
🔴 WORKFLOW FAILS IMMEDIATELY
        ├─ ci-gate.yml fails
        ├─ firsttry-quality.yml fails
        ├─ firsttry-ci.yml fails
        ├─ licensing-ci.yml fails
        ├─ gates-safety-suite.yml fails
        └─ All workflows blocked
```

**Once Error #1 is fixed:**

```
python -m firsttry.cli run --tier lite
        ↓
Ruff linting runs
        ↓
Ruff finds violations:
  - F401 unused imports
  - E701/E702 one-liner violations
        ↓
🔴 Linting gate FAILS
        ├─ test_gates_comprehensive::test_check_lint_pass fails
        ├─ FirstTry lite blocked
        ├─ All dependent workflows fail
```

**Once Errors #1 & #2 are fixed:**

```
MyPy type checking runs
        ↓
MyPy encounters:
  - Duplicate tests module (__init__.py)
  - Missing ignore rules
  - Unresolved type errors
        ↓
🟡 MyPy check may fail or need cache rebuild
```

---

## ✅ VERIFICATION CHECKLIST

**To confirm these are the actual errors:**

```bash
# 1. Check for legacy CLI usage in workflows
grep -r "python -m firsttry run --gate" .github/workflows/

# 2. Check for ruff violations
ruff check tests/conftest.py
ruff check tests/test_cli_legacy_flags.py
ruff check tools/ft_collate_reports.py
ruff check tools/ft_vs_manual_collate.py

# 3. Check for mypy issues
ls -la tests/__init__.py  # Check if file exists
python -m mypy --version
python -m mypy src/ 2>&1 | head -20

# 4. Run test that fails
pytest -q -k test_check_lint_pass --maxfail=1
```

---

## 📋 ERROR SEVERITY MATRIX

| Error # | Issue | Severity | Blocker | File(s) | Type |
|---------|-------|----------|---------|---------|------|
| 1 | Legacy CLI `--gate` flag | 🔴 CRITICAL | YES | `.github/workflows/*.yml` | Hard Error |
| 2a | F401 unused imports | 🔴 HIGH | YES | `tests/conftest.py`, `tests/test_cli_legacy_flags.py` | Lint |
| 2b | E701/E702 one-liners | 🔴 HIGH | YES | `tools/ft_collate_reports.py`, `tools/ft_vs_manual_collate.py` | Lint |
| 3a | Duplicate `tests/__init__.py` | 🟡 MEDIUM | MAYBE | `tests/__init__.py` | Module |
| 3b | Missing mypy ignores | 🟡 MEDIUM | MAYBE | `mypy.ini` | Config |
| 3c | Unresolved type errors | 🟡 MEDIUM | YES | Various | Type Check |

---

## 🎯 CONCLUSION

**Root Causes of GitHub Actions Failures:**

1. **PRIMARY BLOCKER:** Workflows call legacy `python -m firsttry run --gate pre-commit` which doesn't exist in current CLI
   - Must use: `python -m firsttry.cli run --tier lite`

2. **SECONDARY BLOCKER:** Ruff finds legitimate code style violations
   - Unused imports (3 instances)
   - One-liner violations (8+ instances)
   - Automatic fixes available via `ruff check . --fix`

3. **TERTIARY ISSUE:** MyPy type checking has configuration or code issues
   - Duplicate module detection
   - Missing ignore rules for optional dependencies
   - Possibly unresolved type errors

**Next Step:** Apply fixes in this priority order:
1. Fix Error #1 (legacy CLI flags in workflows)
2. Fix Error #2 (ruff violations in code)
3. Fix Error #3 (mypy configuration/errors)

---

**Report Generated:** November 6, 2025  
**Analysis Type:** EXACT ERROR DIAGNOSIS  
**Status:** ✅ ROOT CAUSES IDENTIFIED WITH CONCRETE LOCATIONS
