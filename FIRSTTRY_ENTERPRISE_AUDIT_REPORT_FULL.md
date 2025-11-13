# FirstTry — Full Enterprise Audit Report (Ripgrep-backed)

Date: 2025-11-12
Repo: `Firstry` (owner: arnab19111987-ops)
Target SHA validated earlier in session: `de08844470e4c8170dd8d6fc6f0379391434cd3a` (detached worktree used for verification)

## Scope
This audit is a read-only, evidence-backed inspection of the repository focused on the areas requested:
- CI parity / warm vs full test behavior (testmon, warm path, divergence detection)
- Golden/golden-cache behavior and auto-refresh
- Flaky-tests handling and the `ci/flaky_tests.json` artifact
- Rust fastpath (ft_fastpath) and Python `blake3` fallback
- CLI orchestration, DAG pipeline wiring, timeouts and reporting
- Central config, S3 defaults, and licensing guard behavior

All evidence below comes from repository source files and the ripgrep-based probes executed in the restore environment (ripgrep v11.0.2). Where helpful, I include direct snippets or paraphrases of lines found by `rg` along with file paths.

---

## Methodology
- Create a detached worktree at the requested SHA and created a Python venv.
- Installed the project editably and parity extras where necessary to run `ft pre-commit` locally (logs saved in `/tmp` during the session; see Notes).
- Installed `ripgrep` and ran a suite of `rg` probes to locate code evidence across `src/` and other paths. The probe queries targeted keywords and code patterns you requested (testmon, goldens, flaky, ft_fastpath, blake3, parity_runner, etc.).
- Collected package parity evidence via the environment's pip freeze and audit artifacts (some audit jsons exist in `.firsttry/`) to support claims about installed packages.

Files with collected runtime artifacts from the restore run (not committed):
- `/tmp/restore_install.log` — install log from editable install
- `/tmp/restore_install_parity.log` — parity package installs
- `/tmp/restore_ft.log` — `ft pre-commit` run logs
- `/tmp/restore_requirements.freeze` — freeze of installed env after parity install

I did not change repository source files for this audit. All operations were performed in a detached worktree and local venv.

---

## Executive summary (top line)
- The repo implements a CI-aware warm-path (testmon) + flaky + smoke fallback in `ci_parity/parity_runner.py` and supports a structured DAG-based runner. Evidence shows explicit handling of testmon exit codes and warm/full divergence detection.
- The project has a Python fallback for file hashing using `blake3` and a Rust fastpath module is present (`ft_fastpath/src/lib.rs`) — the Python wrapper falls back to `blake3` when Rust bridge isn't available.
- `ci/flaky_tests.json` is referenced from code but is not present in the repository snapshot (MISSING). That file is expected by some warm-path flows; missing it will make some parity flows rely on fallbacks or cause UNKNOWN behavior in CI reproductions.
- Central config uses `firsttry.toml` and environment variables; S3 usage appears opt-in via `FT_S3_BUCKET`/`FT_S3_PREFIX`.

---

## Detailed findings (with evidence)
Note: snippets below are paraphrased or directly echoed from `rg` results captured during the ripgrep run. File paths are relative to repo root.

### A. testmon & warm path (PASS — testmon present and handled)
Evidence:
- `src/firsttry/ci_parity/parity_runner.py` contains explicit warm-path comments and logic describing the warm path as: "WARM PATH (testmon + flaky + smoke fallback)" and references that "testmon (exit 5 = \"no tests collected\") — no stdout parsing". This shows the code intentionally treats the `pytest-testmon` special exit code and documents it.
- Environment / parity artifacts show `pytest-testmon` present in parity lists and installed env (pip freeze / audit json entries include `pytest-testmon` / version). Example evidence from the audit lists: parity audit files and pip freeze contain `pytest-testmon` (various parity files under `.firsttry/` and freeze files recorded in `/tmp` during restore).
- Search evidence: `rg "testmon" src/` returned occurrences in `src/firsttry/ci_parity/` and `src/firsttry/runners/pytest.py` (i.e., the runner code integrates with testmon).

Impact / notes:
- Warm-path behavior is implemented and accounts for testmon semantics — good for fast local iterations.
- Reproducing CI behavior requires the parity toolchain (exact versions of pytest + plugins) to be present; otherwise, the `ft pre-commit` self-check will report missing plugins (which we observed before installing parity packages).


### B. Golden caches & artifacts (INFO/PARTIAL)
Evidence:
- `rg` found references to `golden_cache`-like strings and cache upload/download patterns in `.github/workflows` files and in code. For example, probes matched `upload.*cache|download.*cache|artifact|s3.*cache` in workflow snippets (where present).
- `.firsttry/ci-extra-requirements.txt` and `.firsttry/constraints.txt` pin `blake3` which is used by the fastpath and caching heuristics.

Impact / notes:
- The codebase includes golden/cache concepts and workflow hints for artifacts, but full behavior depends on CI configuration (S3 targets, credentials) which are intentionally opt-in.


### C. Flaky tests / divergence monitor (WARNING — missing artifact)
Evidence:
- The code references `ci/flaky_tests.json` from `src/firsttry/ci_parity/cache_utils.py` and parity logic; ripgrep probes also found references like `flaky_tests.json` and `flaky` keywords across parity modules.
- The probe returned: `MISSING: ci/flaky_tests.json` (file not present in repo snapshot).

Impact:
- The warm-path flow expects a `ci/flaky_tests.json` to drive flaky-specific inclusion; missing this file means warm-path runs cannot deterministically consult the same flaky set as CI. Recommendation: either commit a CI-managed artifact path or update parity scripts to explicitly handle its absence (e.g., empty list fallback with clear log message).


### D. Rust fastpath vs Python fallback (INFO)
Evidence:
- There is a Rust module source in the tree: `ft_fastpath/src/lib.rs` exists and contains Rust imports such as `use ignore::{WalkBuilder, WalkState};` (probe matched the file.)
- `src/firsttry/twin/fastpath.py` contains comments and code showing a try/except import for `ft_fastpath` and explicit `import blake3  # Ensure available even when Rust path is used`. `rg` matches included lines such as:
  - "# Try to import Rust bridge AND ensure blake3 is available"
  - "import blake3  # Ensure available even when Rust path is used"
  - usage: `h = blake3.blake3()` in the Python fallback path.
- The environment has Python `blake3` installed in the restore venv (pip freeze shows `blake3==1.0.8`).

Impact / recommendation:
- Rust fastpath exists but is optional — the Python fallback is present and deterministic via `blake3`. If you want to enable the Rust bridge for production performance, include a build step (maturin / pyo3) in CI and test packaging.


### E. Timeouts and task definitions (PASS)
Evidence:
- Multiple runner modules define `timeout_s` fields and code calls which pass `timeout=task.timeout_s` into `subprocess.run` or equivalent. Examples found in `src/firsttry/runner/executor.py`, `src/firsttry/runners/*`, and `src/firsttry/ci_parity/parity_runner.py` (many `timeout_s` occurrences).
- Planner and DAG builder add Tasks with explicit `timeout_s` settings (planner and dag files include code that sets `timeout_s=60`, `120`, `300`, etc.).

Impact:
- Execution timeouts are explicit and applied across runners — good for preventing runaway checks. Consider ensuring the timeouts are documented or configurable centrally (some are configurable via env or firsttry.toml patterns already).


### F. CLI orchestration, DAG, and reporting (PASS)
Evidence:
- `src/firsttry/cli.py` contains the primary `main()` and flags such as `--report-json` (pointing to `.firsttry/report.json`), `clear-cache` parser, and `--dag-only` flag references in other CLI variants.
- Reporting utilities: `src/firsttry/reporting/html.py` and `src/firsttry/reporting/tty.py` produce HTML and TTY outputs; the CLI writes `.firsttry/report.json` (report paths and helpers are present).
- The parity runner writes an artifacts report (evidence: `📄 Report written to: {report_path}` in `ci_parity/parity_runner.py`).

Impact:
- The CLI and reporting subsystems are mature and integrated with `.firsttry/report.json`. That enables dashboards and offline report generation.


### G. Central config and license handling (INFO)
Evidence:
- `src/firsttry/config_loader.py`, `src/firsttry/config.py`, and `src/firsttry/sync.py` handle `firsttry.toml` and environment config.
- Licensing code inspects `FIRSTTRY_LICENSE_KEY` environment variable (e.g., `src/firsttry/license.py` reads this variable). The codebase uses environment variables for tier handling and telemetry.

Impact / recommendation:
- Defaults appear to prefer opt-in remote S3 usage. Licensing reads environment keys; ensure secrets are not hardcoded in repo and CI supplies them via secure variables.


### H. S3 default / remote cache (INFO)
Evidence:
- `src/firsttry/cache/s3.py` references `FT_S3_BUCKET`/`FT_S3_PREFIX` and `src/firsttry/cli.py` can read `FT_S3_BUCKET`.
- There is no evidence of an enabled default S3 bucket — behavior is opt-in via env variables.

Impact:
- This is good for security; remote S3 caching is opt-in.


## Missing items & risks (actionable)
1. ci/flaky_tests.json is referenced by parity/warm flows but is not present in the repo snapshot. Risk: non-deterministic warm-path behavior vs CI. Fix: add a small committed placeholder (empty list) or produce a CI step that publishes the artifact into the repo's .firsttry/ artifacts area for local restore runs.

2. Parity toolchain version drift: when reproducing a historical SHA, running `ft pre-commit` failed until parity packages (parity versions) were installed. Risk: local reproduceability of gates requires exact parity packages pinned. Fix: include a documented parity bootstrap script and/or commit a `ci/parity.lock.json` file that is used by `ft pre-commit` to auto-validate and install a local parity env (or record exact package pins in `.firsttry/` constraints).

3. Rust fastpath packaging: Rust sources exist but the Rust Python bridge is optional. If you expect to use the Rust path in CI for performance, add a maturin/pyo3 packaging step in CI and validate wheel availability on CI images.

4. Artifacts & logs: some `.firsttry/logs/*` files were empty in the snapshot; ensure CI preserves relevant artifact logs for audits.


## Repro steps I ran (for auditors)
These are the exact high-level steps I executed inside the detached worktree (kept local and not committed):

- Create worktree at requested SHA:

```bash
git worktree add --detach ../restore-de08844470e4c8170dd8d6fc6f0379391434cd3a de08844470e4c8170dd8d6fc6f0379391434cd3a
cd ../restore-de08844470e4c8170dd8d6fc6f0379391434cd3a
```

- Create and activate venv, install editable plus parity extras (where available):

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e . -r .firsttry/ci-extra-requirements.txt || pip install -e .
```

- Run the FirstTry pre-commit gate and capture logs:

```bash
python -m firsttry.cli pre-commit > /tmp/restore_ft.log 2>&1
# If the gate reports parity self-check errors, install parity packages (observed during run)
# e.g. pip install 'pytest==8.4.2' bandit==1.7.9 pytest-cov pytest-timeout pytest-xdist pytest-rerunfailures pytest-testmon pytest-json-report
# Re-run the gate.
```

- Install ripgrep (on the dev container) and re-run ripgrep-based audit probes (the step used to collect evidence used in this report). Example probe command used inside the repo:

```bash
rg -n --hidden --no-ignore-vcs --glob "!.git" "testmon" src/ | sed -n '1,200p'
```

Logs from these runs are available locally in the dev container under `/tmp/restore_*.log` as listed earlier.


## Recommendations and next steps (prioritized)
1. Low friction: Add or document `ci/flaky_tests.json` handling.
   - Either commit a placeholder `ci/flaky_tests.json` (empty list), or add code to clearly log and continue with an empty flaky list when missing (and fail loudly in CI only).

2. Harden parity reproduction for historical SHAs.
   - Save parity package pins in `.firsttry/parity.lock.json` (or expand `.firsttry/constraints.txt`) and provide a `scripts/bootstrap-parity.sh` to quickly create a parity venv for restores.

3. Packaging for Rust fastpath (if you need it in CI).
   - If Rust fastpath matters for performance, add a `maturin` build step in CI to produce/wheel and test wheel installation in CI images.

4. Artifact hygiene: ensure `.firsttry/logs` contain useful, non-empty artifacts for audits.
   - Configure CI to persist artifacts and upload them to artifacts storage that the audit process can reference.

5. Optional: Add a small QA test that fails if `ci/flaky_tests.json` is referenced but missing, in a 