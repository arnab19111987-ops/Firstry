# Supply Chain Security Remediation Report

**Date:** November 11, 2025  
**Status:** ✅ COMPLETE  
**Severity:** CRITICAL (CVE-2025-47273, CVE-2024-6345)

## Executive Summary

Successfully remediated 2 known vulnerabilities in setuptools affecting the FirstTry development and CI environments. All environments now use setuptools 80.9.0 (fixes applied for CVE-2025-47273 and CVE-2024-6345). Implemented comprehensive supply-chain audit infrastructure with automated CI gates.

## Vulnerabilities Remediated

### 1. PYSEC-2025-49 / CVE-2025-47273 / GHSA-5rjg-fvgr-3xxf
- **Package:** setuptools < 78.1.1
- **Severity:** HIGH
- **Description:** Path traversal vulnerability in `PackageIndex` allowing arbitrary file writes
- **Impact:** Potential remote code execution depending on context
- **Fix:** Upgraded to setuptools 80.9.0

### 2. GHSA-cx63-2mw6-8hw5 / CVE-2024-6345
- **Package:** setuptools < 70.0.0
- **Severity:** HIGH
- **Description:** Code injection vulnerability in `package_index` module download functions
- **Impact:** Remote code execution via user-controlled package URLs
- **Fix:** Upgraded to setuptools 80.9.0

## Remediation Actions Completed

### ✅ 1. Immediate Environment Fixes
- **Dev Container:** Upgraded setuptools from 69.0.3 → 80.9.0
- **Parity venv (.venv-parity):** Upgraded setuptools to 80.9.0
- **pip-audit Results:** Both environments now report "No known vulnerabilities found"

### ✅ 2. Security Constraints Infrastructure
**Created:** `constraints/security.txt`
```txt
# Security-critical pins and floors for Python tooling runtime.
setuptools>=78.1.1
```

**Updated:** `pyproject.toml` build requirements
```toml
[build-system]
requires = ["setuptools>=78.1.1", "wheel"]  # Was: setuptools>=68
```

### ✅ 3. CI Supply-Chain Audit Workflow
**Created:** `.github/workflows/supply-chain-audit.yml`

**Features:**
- Runs on: push to main/release branches, all PRs
- Dual audit mode:
  - Live environment audit (installed packages)
  - Declared inputs audit (requirements files)
- JSON artifact uploads for triage
- Gates PRs on vulnerabilities found
- Respects security constraints during installation

**Permissions:**
- `contents: read`
- `actions: read`
- `security-events: write`

### ✅ 4. Local Development Tooling
**Makefile Targets Added:**
```makefile
make audit-supply    # Run both dev and parity audits
make dev-audit       # Audit dev container environment
make parity-audit    # Audit parity venv
```

**Output Location:**
- `.firsttry/audit-devcontainer.json`
- `.firsttry/audit-parity.json`

### ✅ 5. Pre-commit Integration
**Added to `.pre-commit-config.yaml`:**
```yaml
- id: pip-audit-snapshot
  name: pip-audit (snapshot only)
  entry: bash -c 'mkdir -p .firsttry && (pip-audit -f json -o .firsttry/precommit-audit.json || true) && echo "pip-audit snapshot saved"'
  language: system
  pass_filenames: false
  stages: [pre-commit]
```

**Behavior:**
- Non-blocking (never fails commits)
- Records audit snapshot for local reference
- Developers can review `.firsttry/precommit-audit.json` manually
- CI enforces the hard gates

### ✅ 6. Verification Results
```bash
# Dev container audit
setuptools version: 80.9.0, vulns: 0

# Parity venv audit  
setuptools version: 80.9.0, vulns: 0
```

## Architecture & Integration

### Defense-in-Depth Layers

1. **Build-time:** `pyproject.toml` enforces minimum setuptools version during package build
2. **Install-time:** `constraints/security.txt` applied via `-c` flag ensures runtime floors
3. **Pre-commit:** Local snapshot for developer awareness (non-blocking)
4. **CI Gate:** Workflow fails PRs with vulnerabilities (blocking)
5. **Periodic:** Runs on main branch pushes for ongoing monitoring

### File Structure
```
constraints/
└── security.txt                          # Security-critical version floors
.github/workflows/
└── supply-chain-audit.yml               # Automated CI enforcement
.firsttry/
├── audit-devcontainer.json              # Dev env audit results
├── audit-parity.json                    # Parity venv audit results
└── precommit-audit.json                 # Pre-commit snapshot
```

## Usage Examples

### Local Development
```bash
# Run full audit across both environments
make audit-supply

# Check specific environment
make dev-audit
make parity-audit

# View results
cat .firsttry/audit-devcontainer.json | jq '.dependencies[] | select(.vulns | length > 0)'
```

### CI Integration
```bash
# Install with security constraints
python -m pip install -c constraints/security.txt -e ".[dev]"

# Audit in CI (already automated in workflow)
pip-audit -l -f json -o audit-live.json
```

### Pre-commit Hook
```bash
# Runs automatically on commit (non-blocking)
git commit -m "feat: new feature"
# Output: "pip-audit snapshot saved"

# Manual review
cat .firsttry/precommit-audit.json | jq .
```

## Maintenance & Next Steps

### Recommended Actions
1. **Monitor CI:** Watch first few PR runs to ensure workflow runs cleanly
2. **Update Constraints:** Add other security-critical packages as needed to `constraints/security.txt`
3. **Review Allowlist:** If low-severity findings appear, consider adding an allowlist file
4. **Documentation:** Update developer onboarding docs to mention `make audit-supply`

### Future Enhancements
1. **Severity Thresholds:** Configure workflow to only fail on HIGH/CRITICAL (warn on MEDIUM/LOW)
2. **Dependency Graph:** Add `pip-audit --output cyclonedx` for SBOM generation
3. **Scheduled Scans:** Add weekly cron trigger to catch newly disclosed CVEs
4. **Allowlist File:** Create `.pip-audit-ignore.json` for accepted risks with justification

### Related Work
- **Bandit Findings:** Pending triage (B110, B404, B607 flagged in earlier scan)
- **Secrets Scan:** Review `FIRSTTRY_SHARED_SECRET` default in `src/firsttry/license.py`
- **Code Quality:** Address duplication blocks (~641) and large functions (>50 lines)

## Compliance & Attestation

- ✅ All known setuptools vulnerabilities remediated
- ✅ Automated gates prevent regression
- ✅ Audit trails preserved in JSON artifacts
- ✅ Security constraints enforced across all environments
- ✅ Pre-commit awareness without developer friction

**Verified By:** Automated pip-audit 2.9.0  
**Audit Date:** November 11, 2025  
**Next Review:** Automated on every PR + push to main

---

## Appendix: Audit Evidence

### Dev Container Environment
```json
{
  "dependencies": [
    {
      "name": "setuptools",
      "version": "80.9.0",
      "vulns": []
    }
  ]
}
```

### Parity Venv Environment  
```json
{
  "dependencies": [
    {
      "name": "setuptools",
      "version": "80.9.0",
      "vulns": []
    }
  ]
}
```

### CI Workflow Status
- **File:** `.github/workflows/supply-chain-audit.yml`
- **Triggers:** push (main, release/**), pull_request (main, release/**)
- **Timeout:** 10 minutes
- **Artifacts:** pip-audit-json (audit-*.json, audit-live.json)

---

**Report Generated:** November 11, 2025  
**Tool:** pip-audit 2.9.0  
**Status:** REMEDIATION COMPLETE ✅
