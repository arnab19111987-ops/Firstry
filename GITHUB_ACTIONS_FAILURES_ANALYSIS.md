# GitHub Actions Workflow Failures - Root Cause Analysis

## Summary
Multiple GitHub Actions workflows are failing due to **TWO DISTINCT ISSUES**:

1. **Test Failure** - `test_cli_shows_timing_when_write_fails` - BLOCKING ALL WORKFLOWS
2. **Mypy Type Checking Errors** - 60 errors in `src/firsttry/cli.py` - SECONDARY ISSUE

---

## Issue #1: Test Failure (PRIMARY - BLOCKING)

### Affected Workflows
- ✗ firsttry-quality-gate (fails at `make check`)
- ✗ Fast Gate & CLI Safety Suite (fails in pytest)
- ✗ firsttry-ci (fails in pytest)
- ✗ ci-gate (fails at coverage check)
- ✗ firsttry-quality
- ✗ licensing-ci

### Root Cause
**Test File:** `tests/test_reporting.py::test_cli_shows_timing_when_write_fails` (line 156)

**The Problem:**
```python
cmd += ["--report", "/proc/version"]  # Line 155
proc = _run(cmd, cwd=tmp_path, env=env, timeout=90)
assert proc.returncode == 0, f"CLI should succeed even if report write fails:\n{proc.stderr}"
```

The test uses `--report` flag, but this flag is **ambiguous** in the CLI because it could match either:
- `--report-json`
- `--report-schema`

**Actual CLI Error:**
```
firsttry run: error: ambiguous option: --report could match --report-json, --report-schema
```

**Why It's Failing:**
The argparse argument parser (in `src/firsttry/cli.py`) doesn't have a `--report` option. It has `--report-json` and `--report-schema`. The test is trying to use a shortened flag `--report` which argparse interprets as ambiguous when multiple options start with `--report`.

**Exact Error Output from Logs:**
```
AssertionError: CLI should succeed even if report write fails:
usage: firsttry run [-h] ...
                    [--report-json PATH]
                    [--show-report] [--send-telemetry] [--report-schema {1,2}]
firsttry run: error: ambiguous option: --report could match --report-json, --report-schema
```

---

## Issue #2: Mypy Type Checking Errors (SECONDARY)

### Affected Workflows
- ✗ firsttry-quality-gate (fails at `make check` - mypy step)
- ✓ Fast Gate & CLI Safety Suite (doesn't run mypy, only pytest)
- ✗ firsttry-quality (fails at mypy step)

### Root Cause
**File:** `src/firsttry/cli.py`

**Total Errors:** 60 mypy errors

**Error Categories:**

#### 1. Conditional Function Variant Signature Mismatches (Multiple errors)
```
src/firsttry/cli.py:989: error: All conditional function variants must have identical signatures
  Original: def resolve_ci_plan(repo_root: str) -> list[dict[str, str]] | None
  Redefinition: def resolve_ci_plan(root: Any) -> Any
```

Lines affected: 989, 1042 (and likely more)

**Issue:** Overloaded function definitions have inconsistent signatures. When using `@overload`, all variants must have the same parameter names and types should be more general.

---

#### 2. Missing Type Annotation for Variable
```
src/firsttry/cli.py:1090: error: Need type annotation for "ci_plan"
  hint: "ci_plan: list[<type>] = ..."
```

**Issue:** Variable `ci_plan` is assigned a value but has no explicit type annotation. Mypy needs explicit type hints.

---

#### 3. Union Type Handling Issues
```
src/firsttry/cli.py:1134: error: Item "None" of "dict[str, Any] | None" has no attribute "get"
src/firsttry/cli.py:1201: error: Item "object" of "object | Any" has no attribute "append"
src/firsttry/cli.py:1328-1338: errors with "object" not being indexable
```

**Issue:** Missing None checks or type narrowing. When a variable could be None or object type, you need to handle all union cases before accessing methods/attributes.

---

#### 4. Missing Module Attributes
```
src/firsttry/cli.py:1212: error: Module "firsttry.reporting" has no attribute "write_report_async"
src/firsttry/cli.py:1251: error: Module "firsttry.reporting" has no attribute "write_report_async"
```

**Issue:** Calling `firsttry.reporting.write_report_async()` but this function doesn't exist or isn't exported from the module. This may be a stub function that hasn't been implemented yet.

---

#### 5. Unused Type Ignore Comments (Multiple)
```
src/firsttry/cli.py:1468: error: Unused "type: ignore" comment
src/firsttry/cli.py:1473: error: Unused "type: ignore" comment
src/firsttry/cli.py:1476: error: Unused "type: ignore" comment
src/firsttry/cli.py:1478: error: Unused "type: ignore" comment
src/firsttry/cli.py:1484: error: Unused "type: ignore" comment
src/firsttry/cli.py:1487: error: Unused "type: ignore" comment
src/firsttry/cli.py:1490: error: Unused "type: ignore" comment
src/firsttry/cli.py:1512: error: Unused "type: ignore" comment
src/firsttry/cli.py:1515: error: Unused "type: ignore" comment
src/firsttry/cli.py:1517: error: Unused "type: ignore" comment
```

**Issue:** There are `# type: ignore` comments in the code that are no longer needed (either the code is now correct, or a newer mypy version doesn't need them anymore).

---

## Workflow Failure Chain

```
┌─────────────────────────────────┐
│   Commit to main branch         │
└─────────────────┬───────────────┘
                  │
                  ▼
┌─────────────────────────────────┐
│   GitHub Actions trigger        │
└─────────────────┬───────────────┘
                  │
          ┌───────┴────────┐
          │                │
          ▼                ▼
    ┌──────────┐    ┌────────────────┐
    │ Checkout │    │ Setup Python   │
    └──────────┘    └────────────────┘
          │                │
          └───────┬────────┘
                  │
                  ▼
        ┌──────────────────┐
        │ Install deps     │
        └──────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌────────┐  ┌────────┐  ┌─────────────┐
│ Ruff   │  │ Black  │  │ MyPy (60)   │ ◄─ Issue #2 (SECONDARY)
│ ✓Pass  │  │ ✓Pass  │  │ ✗FAIL       │
└────────┘  └────────┘  └─────────────┘
    │             │             │
    └─────────────┼─────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │ Pytest Tests     │
        └──────────────────┘
                  │
    ┌─────────────┴──────────────┐
    │                            │
    ▼                            ▼
┌──────────────────────┐  ┌──────────────────────┐
│ 258/259 Tests PASS   │  │ test_reporting.py    │
│                      │  │ 1 Test FAILS         │ ◄─ Issue #1 (PRIMARY)
│                      │  │ Ambiguous --report   │
└──────────────────────┘  └──────────────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │ Entire build     │
        │ FAILS            │
        └──────────────────┘
```

---

## Why All Workflows Are Affected

1. **Test Failure (Issue #1) blocks everything:**
   - The pytest step fails with 1 failure
   - ALL workflows that run `make check` or pytest fail
   - This is the immediate visible failure

2. **Mypy Errors (Issue #2) also blocks workflows:**
   - Workflows that run the full quality gate (`make check`) also run mypy
   - 60 mypy errors prevent the gate from passing
   - Some workflows may skip mypy (like the Fast Gate & CLI Safety Suite)

---

## Current Workflow Status

| Workflow | Status | Root Cause |
|----------|--------|-----------|
| firsttry-quality-gate | ✗ FAIL | Test failure + Mypy errors |
| Fast Gate & CLI Safety Suite | ✗ FAIL | Test failure (no mypy check) |
| firsttry-ci | ✗ FAIL | Test failure |
| ci-gate | ✗ FAIL | Test failure (fails coverage check due to test failure) |
| firsttry-quality | ✗ FAIL | Mypy errors |
| licensing-ci | ✗ FAIL | Test failure |
| FirstTry Proof | ✓ PASS | Doesn't run mypy/pytest on full suite |
| node-ci | - | Not checked (JavaScript workflow) |

---

## Exact Failure Information

### Test Failure Output
```
tests/test_reporting.py::test_cli_shows_timing_when_write_fails
AssertionError: CLI should succeed even if report write fails:
usage: firsttry run [-h] [--profile {fast,dev,full,strict}]
                    [--tier {free-fast,free-lite,lite,pro,strict}]
                    [--source {auto,config,ci,detect}] [--changed-only]
                    [--no-cache] [--cache-only] [--run-npm-anyway]
                    [--debug-phases] [--interactive] [--report-json PATH]
                    [--show-report] [--send-telemetry] [--report-schema {1,2}]
                    [--dry-run]
                    [{auto,fast,strict,ci,config,pro,teams,full,promax,enterprise,q,c,t,p,e}]
firsttry run: error: ambiguous option: --report could match --report-json, --report-schema

assert 2 == 0 (return code mismatch)
```

### Mypy Error Sample
```
src/firsttry/cli.py:989: error: All conditional function variants must have identical signatures [misc]
src/firsttry/cli.py:1090: error: Need type annotation for "ci_plan" [var-annotated]
src/firsttry/cli.py:1134: error: Item "None" of "dict[str, Any] | None" has no attribute "get" [union-attr]
src/firsttry/cli.py:1212: error: Module "firsttry.reporting" has no attribute "write_report_async" [attr-defined]
src/firsttry/cli.py:1468: error: Unused "type: ignore" comment [unused-ignore]
Found 60 errors in 15 files (checked 313 source files)
```

---

## Summary Table

| Issue | Type | Severity | Affected Files | Test Status | Impact |
|-------|------|----------|-----------------|------------|--------|
| Ambiguous `--report` flag | Test Logic | **CRITICAL** | `tests/test_reporting.py:156` | 1 FAILED | Blocks ALL workflows |
| Mypy errors in cli.py | Type Checking | **HIGH** | `src/firsttry/cli.py` | 60 errors | Blocks quality workflows |

---

## Next Steps Required

1. **Fix Test (URGENT - BLOCKS ALL WORKFLOWS)**
   - Use `--report-json` instead of `--report` in test line 155
   - Or add explicit `--report` option to CLI argparse

2. **Fix Mypy Errors (HIGH PRIORITY)**
   - Fix conditional function variant signatures
   - Add missing type annotations
   - Handle Union types properly (None checks)
   - Implement or stub `write_report_async` function
   - Remove unused `type: ignore` comments

