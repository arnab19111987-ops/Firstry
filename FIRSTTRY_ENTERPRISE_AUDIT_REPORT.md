# FirstTry Repository – Enterprise Read-Only Audit
Mode: Detection-only
Date: 2025-11-12
Branch: chore/artifact-actions-v4


## Tier Summary Table

| Tier | Status | Key Findings | Notes |
|------|--------|---------------|-------|
| Developer | ⚠️ Partial Pass | CLI import/collection broadly successful, but type- and runtime-issues remain (mypy errors and some runner signature mismatches). | Import-only pytest collection passed (153 passed, 4 skipped, 918 deselected) but mypy (CI config) reported many errors (68 errors in 17 files in a recent run). See details below. |
| Team | ⚠️ Partial Pass | Strong CI/workflow coverage and parity assets exist, but some parity artifacts reference paths or snapshot locations that may not exist locally (e.g., `.firsttry` runtime artifacts). Pre-commit configuration injects a test secret for parity. | Many `.github/workflows/*.yml` are present (supply-chain-audit, parity/ci workflows). `ci/parity.lock.json` exists. See Team Audit section. |
| Enterprise | ⚠️ Partial Pass | Dependency scanning (pip-audit) is clean; Bandit surfaced low-risk findings (B110/B404/B607). A shared-secret pattern exists in `src/firsttry/license.py` with an explicit test/dev fallback; this requires manual review. LICENSE file present (Apache-2.0). | Security tooling is wired, but a few policy gaps & SAST findings remain. See Enterprise Audit section. |


---

## 1) Developer Audit

Scope scanned (read-only): `pyproject.toml`, `pytest.ini`, `.pre-commit-config.yaml`, `src/firsttry/**`.

Findings (detection-only):

- CLI / import health
  - Import-stage collection (focused import-only pytest run) returned: 153 passed, 4 skipped, 918 deselected (this run exercised import/collection stability rather than full test execution). This shows the codebase imports without immediate crash in many modules.
  - Several runners and legacy async/sync contracts show typing/signature mismatches. A recent mypy run using CI config reported 68 errors in 17 files (representative problem areas below).

- Measured tooling/typing results (read-only evidence)
  - Mypy (CI config `.firsttry/mypy-ci.ini`) run: Found 68 errors in 17 files. Representative error categories captured during the run:
    - Incompatible default for arguments that now require Optional typing (PEP 484/no_implicit_optional): files like `performance_targets.py`, `smart_npm.py`, `parallel_pytest.py`, `smart_pytest.py`.
    - Runner signature mismatches / Protocol overrides (`CheckRunner` vs legacy async runners): `src/firsttry/runners/*` (python/js/deps/ci_parity/custom etc.) reported `Signature of "run" incompatible with supertype "CheckRunner"` and `attr-defined` errors for helper attributes (e.g., `run_cmd`).
    - Package-level re-export / attr-defined complaints: `orchestrator.py`, `cli_*` modules referencing `firsttry.planner.build_plan` etc. (some of these were surfaced by mypy as "module has no attribute ...").
  - pytest configuration: `pyproject.toml` contains `tool.pytest.ini_options` and `pytest.ini` also configures warnings and a `testmon` cache path `.firsttry/warm/testmon`. Note: `.firsttry` directory is referenced by config but not all `.firsttry/*` artifacts are present by default in a fresh checkout (they are created at runtime by pre-commit or CI jobs).

- Deprecated / unused modules
  - No systematic deprecation annotations found during the read-only pass; however, large CLI modules (`src/firsttry/cli.py`, related CLI variants) contain complex, long functions (observed by file sizes and organizational patterns in `src/firsttry/`). This increases maintenance risk but is not a direct failure for developer tier.

Developer Tier: status justification
- Partial Pass (⚠️): imports and CLI entrypoints import successfully in many cases; however static typing and some interface contracts are not yet fully clean (mypy errors) and will block strict CI `--config-file .firsttry/mypy-ci.ini` gating until resolved.


---

## 2) Team Audit

Scope scanned (read-only): `.github/workflows/*.yml`, `.pre-commit-config.yaml`, `ci/parity.lock.json`, `pyproject.toml` dependencies.

Findings:

- CI / workflows
  - Many workflows exist under `.github/workflows/` including `supply-chain-audit.yml`, `ci.yml`, `ci-parity.yml`, `firsttry-ci-parity.yml`, `supply-chain-audit.yml`, `quality.yml`, `firsttry-quality.yml`, `firsttry-ci.yml`, `firsttry-proof.yml` and others. This indicates a mature CI surface with specialized gating (supply-chain, parity, quality).
  - `ci/parity.lock.json` exists and enumerates specific versions for `mypy`, `ruff`, `pytest`, `bandit` and args/timeout expectations. This is a positive signal for CI/local parity.

- Pre-commit and local parity
  - `.pre-commit-config.yaml` is present and includes ruff, black, isort, and mypy hooks. There are local hooks that run `ft-pre-commit` and hardcoded test-secret export lines (e.g., `export FT_ENV=test FIRSTTRY_SHARED_SECRET=test-secret-DO-NOT-USE-IN-PROD-0123456789abcdef0123 ...`) used for local parity/dry-run. This is detection-only: it shows tests do inject a deterministic test secret when running parity hooks.
  - The pre-commit config also writes a pip-audit snapshot to `.firsttry/precommit-audit.json` (hook `pip-audit-snapshot`) — the repository expects `.firsttry` to be writable in pre-commit runs.

- Missing / runtime-created artifacts
  - `.firsttry` directory is referenced in config (pre-commit and pytest) but may not exist by default in a fresh checkout — it is created by hooks or CI runs. This is expected, but worth calling out because certain read-only checks (or early test runs) may surface warnings until `.firsttry` is created by a pre-commit or CI job.

- Dependency/tooling presence
  - `pyproject.toml` lists dev dependencies under `[project.optional-dependencies.dev]` including pinned versions of `ruff==0.6.9`, `mypy==1.11.2`, `pytest==8.3.3`, `bandit==1.7.9`. The `ci/parity.lock.json` indicates CI expects `mypy==1.18.2` / `pytest==8.4.2` (parity lock differs from `pyproject.toml.dev`) — this suggests two places of truth for dev tooling versions (one in `pyproject` optional dev set and one in `ci/parity.lock.json`), which can confuse local devs vs CI environments. Detection-only: these version sources are present and should be reconciled.

- Test coverage and gating
  - Project has coverage gating settings present (`tool.firsttry.coverage` in `pyproject.toml`) and CI parity entries for pytest coverage collection. Tests are many; earlier import-only run was successful for the import stage but a full parity pytest (with coverage) was not executed during this detection run.

Team Tier: status justification
- Partial Pass (⚠️): Team-level tooling and CI assets are comprehensive (workflows, parity lock). There are some operational mismatches to note: `.firsttry` is a runtime artifact used by hooks, and there are two places that can diverge for dev tool versions (`pyproject.toml` dev extras vs `ci/parity.lock.json`). These are reconciliation items (not immediate breakage), but they reduce local/CI predictability until aligned.


---

## 3) Enterprise Audit (Security, Compliance, Telemetry)

Scope scanned (read-only): `src/firsttry/**`, `.github/workflows/*`, `pyproject.toml`, `.pre-commit-config.yaml`, `ci/parity.lock.json`, `LICENSE`, `pytest.ini`.

Findings (detection-only):

- License / governance
  - LICENSE file exists at repository root and contains an Apache License, Version 2.0 text (file `LICENSE`). Good: legal artifact present.
  - Missing higher-level governance docs (detection-only): no `SECURITY.md`, `CODE_OF_CONDUCT.md`, or `CONTRIBUTING.md` were detected in the repository root during this read-only pass. Those are often recommended for enterprise distribution.

- Secrets & license gating
  - `src/firsttry/license.py` contains a shared-secret selection strategy and a typed `DEFAULT_SHARED_SECRET` constant that may be used in test/dev modes. The file implements an import-time guard that raises when `CI=true` and a valid env secret is not present — this is a detection of explicit enforcement. However, the code contains fallback semantics used for test/dev runs (detection-only: evidence exists). Key snippets detected:
    - A typed default: `DEFAULT_SHARED_SECRET: str = os.getenv("DEFAULT_SHARED_SECRET", "DO-NOT-USE-IN-PROD")` (read-only evidence)
    - Environment lookups for `FIRSTTRY_SHARED_SECRET`, `FT_SHARED_SECRET` and enforcement checks that raise `RuntimeError` if missing in production-like environments.
  - `.pre-commit-config.yaml` reveals a pre-commit hook that sets `FIRSTTRY_SHARED_SECRET=test-secret-DO-NOT-USE-IN-PROD-0123456789abcdef0123` for parity/dry-run. This demonstrates a practice of using a known test secret during pre-commit runs (detection-only; do not change it here).

- SAST / dependency scanning
  - pip-audit: earlier detection run reported "No known vulnerabilities found" using pip-audit (evidence of dependency scanning configured and a clean result at time of run).
  - Bandit SAST: Bandit runs are present in CI and the parity lock references `bandit==1.7.9`. Earlier Bandit scan (automated audit evidence) flagged 3 low-severity items (B110: try/except/pass; B404: subprocess import usage; B607: start process with partial path). Locations of interest from detection evidence:
    - `src/firsttry/cache/__init__.py` and `src/firsttry/cache/local.py` (B110)
    - `src/firsttry/change_detector.py` (B607) and multiple subprocess uses flagged for B404.

- Telemetry & audit artifacts
  - A telemetry module exists (`src/firsttry/telemetry.py`) — detection-only: telemetry is implemented in the codebase but the audit did not verify runtime collection policies or destinations.
  - Audit snapshot artifacts: pre-commit hook writes `pip-audit` output to `.firsttry/precommit-audit.json` during pre-commit runs. `ci/parity.lock.json` indicates that CI collects coverage artifacts (e.g., `artifacts/coverage.xml`) in parity mode.

- Untracked / unverified external dependencies
  - `pyproject.toml` declares core dependencies (PyYAML, ruff, black, mypy, pytest) and optional `enterprise` dependencies (boto3). The repository contains an SBOM/Supply Chain workflow (`.github/workflows/supply-chain-audit.yml`) but no automatic SBOM generation file was detected (e.g., no `cyclonedx` invocation was found in the scanned files). The `ci/parity.lock.json` and workflows indicate supply-chain scanning is configured in CI.

Enterprise Tier: status justification
- Partial Pass (⚠️): Security controls and scanning are present and active (pip-audit, Bandit, CI gating). A LICENSE is present. Notable findings for follow-up (detection-only): Bandit low findings exist; a shared-secret pattern and pre-commit test-secret injection are present (which is acceptable for parity but must be reviewed for production policies); governance docs like `SECURITY.md` are missing.


---

## 4) Final Summary — Findings by Severity (detection-only)

- 🟥 Critical
  - None detected in automated scan runs during this read-only audit. (No critical CVEs found by pip-audit and no high Bandit items were reported.)

- 🟧 Moderate
  - mypy (CI config) reported many typing errors (68 errors across 17 files). This is a moderate engineering-quality blocker because CI pre-push/pre-commit hooks reference `.firsttry/mypy-ci.ini` and will block strict gating until resolved.
  - Discrepancy between dev-tool version lists: `pyproject.toml` optional dev dependencies vs `ci/parity.lock.json` (may cause local/CI mismatch).

- 🟩 Low
  - Bandit low-severity findings (B110, B404, B607) in cache and subprocess areas. Locations: `src/firsttry/cache/__init__.py`, `src/firsttry/cache/local.py`, `src/firsttry/change_detector.py` and other subprocess call sites.
  - Missing governance docs: `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md` not present in repo root (detection-only).
  - `.firsttry` runtime artifacts referenced by config but not committed; hooks create these artifacts during pre-commit runs.


### Next-step recommendations (detection-only — no fixes applied here)
- High-level follow-ups for each tier (do not apply changes in this run):
  - Developer
    - Run `mypy --config-file .firsttry/mypy-ci.ini` locally and iterate to fix or narrow the 68 reported typing errors; focus on runner signatures and Optional default annotations.
    - Run a full pytest parity run (CI-configured args in `ci/parity.lock.json`) to validate test/coverage gates locally in an isolated environment.

  - Team
    - Reconcile dev-tool version sources: align `pyproject.toml` dev extras and `ci/parity.lock.json` to the single source-of-truth used by CI.
    - Document `.firsttry` artifacts and ensure a developer guide step or `make` target bootstraps required runtime dirs for pre-commit.

  - Enterprise
    - Triage Bandit low findings and justify or remediate the flagged patterns.
    - Document secret-management policy and review `src/firsttry/license.py` fallback/test secret semantics to ensure production cannot use insecure defaults; ensure pre-commit/test secret injection is restricted to local/test runs only.
    - Add `SECURITY.md` and a vulnerability disclosure process, and confirm license metadata in `pyproject.toml` matches the `LICENSE` file (Apache-2.0 found at repo root).


---

## Appendix — Evidence & notable files (read-only)

- `pyproject.toml` — project metadata, dev extras and tool configs (black/ruff/isort/mypy/pytest settings).
- `ci/parity.lock.json` — CI parity lock and expected tool versions/args.
- `.pre-commit-config.yaml` — pre-commit hooks including pip-audit snapshot, ft pre-commit parity hooks, and mypy/ruff/isort/black hooks.
- `pytest.ini` — contains pytest filtering and `testmon` cache path `.firsttry/warm/testmon`.
- `LICENSE` — Apache License, Version 2.0 present at repo root.
- `src/firsttry/license.py` — shared-secret lookup, import-time guard and typed `DEFAULT_SHARED_SECRET` detection.
- Recent mypy run (CI config): 68 errors in 17 files (representative error categories summarized in the Developer Audit section). See earlier console evidence in the repo run logs for exact line-level errors.
- Bandit evidence: CI parity config and previous automated audit output listing B110/B404/B607 flagged files.
- pip-audit evidence: earlier run reported no known vulnerabilities.


---

Report generated in read-only mode. This audit contains only detection and reporting; no files were modified in this operation.

