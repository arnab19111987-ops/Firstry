# Safe Configuration Implementation Checklist

**Goal:** Implement license + S3 configuration WITHOUT breaking existing code

**Approach:** Create separate `license_config.py` file (not replacing `config.py`)

---

## ✅ Pre-Implementation Verification

- [x] Identified all breaking issues (4 critical)
- [x] Analyzed impact scope (325 tests would fail)
- [x] Confirmed safe approach (separate files)
- [x] Created impact report: `CONFIG_MIGRATION_IMPACT_REPORT.md`
- [x] Created verification summary: `CONFIG_VERIFICATION_SUMMARY.txt`

---

## 📋 Phase 1: Create New Files

### Step 1.1: Create `src/firsttry/license_config.py`
- [ ] File created with your proposed code
- [ ] Function: `load_license_config()` (NOT `load_config()`)
- [ ] Types: `LicenseCfg`, `S3Cfg`, `AppCfg`
- [ ] Exports: `s3_prefs()`, `_load_toml()`, etc.
- [ ] Status: Ready for import

**Verification:**
```bash
python -c "from firsttry.license_config import load_license_config; print('OK')"
```

### Step 1.2: Create `src/firsttry/s3_uploader.py`
- [ ] File created with your S3 upload logic
- [ ] Import: `from .license_config import load_license_config`
- [ ] Import: `from .license_config import s3_prefs`
- [ ] Functions: `s3_preflight()`, `s3_upload()`, `s3_upload_many()`
- [ ] Status: Ready for use

**Verification:**
```bash
python -c "from firsttry.s3_uploader import s3_preflight; print('OK')"
```

### Step 1.3: Create `src/firsttry/doctor.py`
- [ ] File created with diagnostic logic
- [ ] Import: `from .license_config import load_license_config`
- [ ] Import: `from .s3_uploader import s3_preflight, s3_prefs`
- [ ] Function: `main()` entry point
- [ ] Status: Ready for CLI

**Verification:**
```bash
python -m firsttry.doctor
# Should output: "FirstTry Doctor" header
```

### Step 1.4: Create `src/firsttry/__main__.py`
- [ ] File created with CLI router
- [ ] Route: `python -m firsttry doctor` → `doctor.main()`
- [ ] Fallback: Try to load existing CLI
- [ ] Status: Router ready

**Verification:**
```bash
python -m firsttry doctor
# Should run doctor successfully
```

---

## 🔍 Phase 2: Verify No Breakage

### Step 2.1: Check Existing `config.py` Untouched
- [ ] `src/firsttry/config.py` NOT modified
- [ ] Still has `Config` class
- [ ] Still has `Timeouts` class
- [ ] Still has `Workflow` class
- [ ] Still exports `load_config(repo_root)`
- [ ] Still exports `timeout_for(cfg, check_id)`
- [ ] Still exports `workflow_requires(cfg)`

**Verification:**
```bash
python -c "from firsttry.config import Config, load_config, timeout_for, workflow_requires; print('OK')"
```

### Step 2.2: Verify `run_swarm.py` Still Works
- [ ] File NOT modified
- [ ] Imports still work
- [ ] Function calls still work
- [ ] No breaking changes

**Verification:**
```bash
python -c "from firsttry.run_swarm import run_swarm; print('OK')"
```

### Step 2.3: Verify CLI Router Works
- [ ] `python -m firsttry doctor` runs without error
- [ ] Output includes "FirstTry Doctor" header
- [ ] License section shows (OK or MISSING)
- [ ] S3 section shows (OK or DISABLED)

**Verification:**
```bash
python -m firsttry doctor
# Expected output:
# FirstTry Doctor
# ───────────────
# Python: /usr/bin/python
# Config: ...
# License: OK (or MISSING)
# S3: OK (or DISABLED)
```

---

## ✅ Phase 3: Run Test Suite

### Step 3.1: Full Test Run
- [ ] Run: `pytest tests/ -v`
- [ ] Expected: All 325 tests PASS
- [ ] No failures
- [ ] No regressions

**Verification:**
```bash
pytest tests/ -v 2>&1 | tail -5
# Expected:
# ===== 325 passed in X.XXs =====
```

### Step 3.2: Type Checking
- [ ] Run: `mypy src/firsttry/{license_config,s3_uploader,doctor}.py`
- [ ] Expected: "Success: no issues found"
- [ ] No type errors

**Verification:**
```bash
mypy src/firsttry/license_config.py
mypy src/firsttry/s3_uploader.py
mypy src/firsttry/doctor.py
```

### Step 3.3: Linting
- [ ] Run: `ruff check src/firsttry/{license_config,s3_uploader,doctor}.py`
- [ ] Expected: All checks pass
- [ ] No linting errors

**Verification:**
```bash
ruff check src/firsttry/license_config.py src/firsttry/s3_uploader.py src/firsttry/doctor.py
```

### Step 3.4: Formatting
- [ ] Run: `black src/firsttry/{license_config,s3_uploader,doctor}.py`
- [ ] Run: `black --check src/firsttry/{license_config,s3_uploader,doctor}.py`
- [ ] Expected: All formatted correctly

**Verification:**
```bash
black src/firsttry/license_config.py src/firsttry/s3_uploader.py src/firsttry/doctor.py
black --check src/firsttry/license_config.py src/firsttry/s3_uploader.py src/firsttry/doctor.py
```

---

## 🚀 Phase 4: Functional Testing

### Step 4.1: Test License Config Loading
- [ ] Create test TOML with `[license]` section
- [ ] Load with: `load_license_config()`
- [ ] Verify: Returns correct license key
- [ ] Verify: Returns correct tier

**Test Code:**
```python
from firsttry.license_config import load_license_config
cfg = load_license_config()
assert cfg.get("license", {}).get("key") == "..."
assert cfg.get("license", {}).get("tier") == "..."
```

### Step 4.2: Test S3 Config Loading
- [ ] Create test TOML with `[s3]` section
- [ ] Load with: `s3_prefs()`
- [ ] Verify: Returns bucket, region, endpoint, prefix
- [ ] Verify: Respects environment overrides

**Test Code:**
```python
from firsttry.s3_uploader import s3_prefs
enabled, bucket, region, endpoint, prefix, ak, sk = s3_prefs()
assert bucket == "..."
assert region == "..."
```

### Step 4.3: Test S3 Preflight
- [ ] Call: `s3_preflight()` with disabled S3
- [ ] Verify: Returns (False, "S3 disabled...")
- [ ] Call: `s3_preflight()` with enabled S3 + no creds
- [ ] Verify: Returns (False, "Missing AWS creds...")
- [ ] Call: `s3_preflight()` with all valid
- [ ] Verify: Returns (True, "")

**Test Code:**
```python
from firsttry.s3_uploader import s3_preflight
ok, reason = s3_preflight()
# Check result based on config
```

### Step 4.4: Test Doctor Output
- [ ] Run: `python -m firsttry doctor`
- [ ] Verify: License status displayed
- [ ] Verify: S3 status displayed
- [ ] Verify: Helpful tips shown
- [ ] Exit code: 0 (success)

---

## 📝 Phase 5: Documentation

### Step 5.1: Create User Guide
- [ ] Document: How to set up config file
- [ ] Document: Where to place `config.toml`
- [ ] Document: Example config (safe defaults)
- [ ] Document: Environment variable overrides
- [ ] File: `docs/CONFIGURATION.md`

### Step 5.2: Create Setup Instructions
- [ ] Document: One-liner to create config
- [ ] Document: How to enable S3
- [ ] Document: How to export AWS creds
- [ ] Document: How to verify setup with doctor
- [ ] File: `docs/SETUP.md`

### Step 5.3: Update README
- [ ] Add link to setup guide
- [ ] Add link to configuration docs
- [ ] Mention: `python -m firsttry doctor`

---

## ✨ Phase 6: Integration

### Step 6.1: Wire S3 Upload to Benchmark Harness
- [ ] Modify benchmark harness to optionally upload
- [ ] Use: `s3_preflight()` to check readiness
- [ ] Use: `s3_upload_many()` to upload artifacts
- [ ] Log: Clear messages (skip reason or success)

**Code Pattern:**
```python
from firsttry.s3_uploader import s3_preflight, s3_upload_many

if args.upload_s3:
    ok, reason = s3_preflight()
    if not ok:
        print(f"[SKIP] S3 upload: {reason}")
    else:
        okc, failc, msgs = s3_upload_many(artifacts)
        for m in msgs:
            print(m)
```

### Step 6.2: Wire License Checking (Optional)
- [ ] Modify tier-restricted features to check license
- [ ] Use: `load_license_config()`
- [ ] Check: `cfg.get("license", {}).get("tier")`
- [ ] Enforce: Tier restrictions if needed

---

## ✅ Final Verification Checklist

- [ ] All 4 new files created
- [ ] No modifications to `config.py`
- [ ] No modifications to `run_swarm.py`
- [ ] No modifications to existing code
- [ ] All 325 tests passing
- [ ] mypy clean
- [ ] ruff clean
- [ ] black formatted
- [ ] `python -m firsttry doctor` works
- [ ] License config loads correctly
- [ ] S3 config loads correctly
- [ ] S3 preflight validation works
- [ ] User documentation created

---

## 🎯 Success Criteria

✅ **PASS if:**
- All 325 existing tests still pass
- No breaking changes to `config.py` or `run_swarm.py`
- New doctor command works
- S3 upload (when enabled) works
- License config loading works
- No type errors, linting errors, or formatting issues

❌ **FAIL if:**
- Any existing test fails
- Any breaking changes detected
- Doctor command doesn't run
- S3 functions crash
- Type/lint/format issues

---

## Rollback Plan

If issues occur:
1. Delete: `src/firsttry/license_config.py`
2. Delete: `src/firsttry/s3_uploader.py`
3. Delete: `src/firsttry/doctor.py`
4. Delete: `src/firsttry/__main__.py`
5. Verify: Tests pass again
6. Result: Back to baseline (zero changes)

---

**Status:** Ready for implementation

**Approval:** User confirmation required before proceeding

**Next Step:** Proceed with Phase 1 (create files)?

