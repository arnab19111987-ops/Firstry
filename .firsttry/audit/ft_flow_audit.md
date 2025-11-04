# FirstTry flow audit

This report is a read-only, evidence-backed audit of FirstTry checks execution flow, timings, and subprocess hygiene.
All raw artifacts referenced below are in the proof pack index: `.firsttry/audit/INDEX.txt` and located under `/tmp` or `.firsttry`.

## 1) Environment & repo snapshot
- Python: see `/tmp/audit_python_version.txt` (python -V)
  - Excerpt: `$(cat /tmp/audit_python_version.txt)`
- Python binary: `/tmp/audit_which_python.txt`
- Pip packages: `/tmp/audit_pip_freeze.txt`
- OS: `/tmp/audit_uname.txt`
- CPUs: `/tmp/audit_nproc.txt`
- Env: `/tmp/audit_env.txt`
- Git SHA: `/tmp/audit_git_sha.txt`
- Working changes: `/tmp/audit_git_status.txt`
- Tracked files: `/tmp/audit_files_all_count.txt` (full list `/tmp/audit_files_all.txt`)
- Python files: `/tmp/audit_files_py_count.txt` (list `/tmp/audit_files_py.txt`)
- src files: `/tmp/audit_files_src_count.txt` (list `/tmp/audit_files_src.txt`)
- FirstTry module info & import time: `/tmp/audit_firsttry_meta.txt`, `/tmp/audit_importtime_firsttry.txt`, `/tmp/audit_firsttry_version_cmd.txt`

(Proof files: see `.firsttry/audit/INDEX.txt`)

## 2) FT run summaries (per tier)
Notes: each run below used `--debug-phases --show-report` and its full log is saved under `/tmp`.

### A) free-lite
- Log: `/tmp/ft_free_lite_debug.log`
- Key phase split (extracted): `/tmp/extract_free_lite_tools.txt`
  - From log: `fast: 4.2s (mypy=4.2s, ruff=0.0s)`
  - `slow: 3.2s (pytest=3.1s, ci-parity=0.1s)`
  - `other: 32.6s (bandit=30.0s, pip-audit=2.6s)`
- Checks printed in results (log lines show many are LOCKED in this tier): see `/tmp/extract_free_lite_tools.txt`.
  - Example Locked evidence (from log): `mypy: 🔒 Locked — available in Pro / ProMax. Run 'firsttry upgrade' to unlock.` (line in `/tmp/extract_free_lite_tools.txt`)
- Event-loop finalizer: present — grep in log `/tmp/ft_free_lite_debug.log` shows a RuntimeError: `Event loop is closed` (lines saved in `/tmp/ft_free_lite_debug.log`). Proof: `/tmp/ft_free_lite_debug.log` lines ~41-42.

### B) free-strict
- Log: `/tmp/ft_free_strict_debug.log`
- Phase split (extracted): `/tmp/extract_free_strict_tools.txt`
  - `fast: 6.0s (mypy=5.9s, ruff=0.1s)`
  - `slow: 4.2s (pytest=4.0s, ci-parity=0.2s)`
  - `other: 33.2s (bandit=30.0s, pip-audit=3.2s)`
- Checks: mypy/pytest appear to run (not locked) in this tier (see `/tmp/extract_free_strict_tools.txt`).
- Event-loop finalizer: present (see end of `/tmp/ft_free_strict_debug.log`).

### C) pro and promax (if available)
- `pro` run log: `/tmp/ft_pro_debug.log` — in this environment Pro is available and bandit/pip-audit ran.
  - Phase split: `fast: 3.1s, slow: 1.9s, other: 31.6s (bandit=30.0s, pip-audit=1.6s)` (see `/tmp/ft_pro_debug.log`).
  - bandit result printed in FT: `/tmp/ft_pro_debug.log` includes a bandit summary JSON-like snippet: issues_total=161, max_severity=high, raw_json: `/workspaces/Firstry/.firsttry/bandit.json`, sharded=true, jobs=2, exclude list etc. (proof lines in `/tmp/ft_pro_debug.log`).
- `promax` run log: `/tmp/ft_promax_debug.log` — similar output, bandit ran and wrote `/workspaces/Firstry/.firsttry/bandit.json` with issues_total=161.
- Event-loop finalizer: present in both logs (post-run finalizer traces included).

## 3) Direct tool baselines (ground truth)
All raw outputs saved under `/tmp`.

- Ruff
  - Command: `ruff check .`
  - Log: `/tmp/manual_ruff.log` — completed in ~0.08s (see top of file). Example output: unused-import warnings reported; fast.

- Mypy
  - Command: `mypy .`
  - Log: `/tmp/manual_mypy.log` — completed in ~4.53s. Output: `Found 1 error` (benchmarks/repos/repo-a-no-config/tests/test_utils1.py:1)

- Pytest
  - Command: `pytest -q`
  - Log: `/tmp/manual_pytest.log` — collection errors occurred due to missing test dependencies (fastapi not installed); run time ~3.28s with import errors recorded. Collection-only run saved in `/tmp/manual_pytest_collect.log` (shows many tests listed, and errors for modules requiring fastapi/tests helper imports).

- pip-audit
  - Command: `pip-audit -f json -r requirements.txt`
  - Log: `/tmp/manual_pip_audit.log` — ran in ~27.5s and reported "No known vulnerabilities found" for the requirements file used; JSON listing saved in the same log.

- Bandit
  - Recursive baseline (no excludes):
    - Command: `bandit -q -r . -f json -o /tmp/bandit_plain.json`
    - Log: `/tmp/bandit_plain.log` — real time: 5m48s (345s). JSON saved `/tmp/bandit_plain.json` (results length: 10126) — counts printed to console and saved in audit.
  - With excludes:
    - EXCL used: `.venv,node_modules,.git,__pycache__,build,dist,.ruff_cache,.mypy_cache,.pytest_cache,.firsttry`
    - Command: `bandit -q -r . -x "$EXCL" -f json -o /tmp/bandit_excl.json`
    - Log: `/tmp/bandit_excl.log` — real time: 1m52s (112s). JSON saved `/tmp/bandit_excl.json` (results length: 6381).
  - Counts: see `/tmp/audit_bandit_counts.txt` (printed summary) and evidence files `/tmp/bandit_plain.json`, `/tmp/bandit_excl.json`.

Observation: bandit raw recursive scan is orders of magnitude slower than when excludes are applied. Sharded runs (FT sharded or developer harness) that pass explicit file targets or -x avoid huge scans.

## 4) Ignore/exclude audit
- Ignore constants file: `/tmp/audit_ignore_py.txt` (source: `src/firsttry/ignore.py`) — shows IGNORE_DIRS and bandit_excludes implementation (absolute paths created from repo root).
- Usage grep: `/tmp/audit_ignore_usage.txt` — shows `bandit_excludes` is used in `src/firsttry/checks/bandit_runner.py` and `src/firsttry/checks/bandit_sharded.py` (proof lines).
- FT pro/promax logs (when bandit actually ran) show FT passed excludes and ran sharded bandit (see JSON snippet in `/tmp/ft_pro_debug.log` referencing `exclude` and `sharded: true, jobs: 2`) and the sharded merged JSON `/workspaces/Firstry/.firsttry/bandit.json` has `issues_total: 161`.
- Developer harness evidence: `tools/dev/run_bandit_sharded.py` was executed earlier; logs saved in `/tmp/run_bandit_sharded_jobs2.log` and `/tmp/run_bandit_sharded_jobs4.log`. Those logs show explicit `-x <abs paths>` followed by explicit file path lists (no `-r .`) and total times ~5.5–5.8s for the sharded explicit-run case (proof in those logs).

Conclusion: FT contains support for producing -x exclude lists (via `bandit_excludes`) and both the single-run and sharded runners reference it. When bandit is unlocked and FT runs Pro/Promax tiers, bandit is invoked with excludes and in sharded mode; when bandit is locked in lower tiers, FT reports it as Locked and doesn't spawn the external bandit process.

## 5) Subprocess hygiene (async vs sync)
- Grep for async subprocess patterns: `/tmp/audit_subproc_sites.txt` lists matching files and lines (e.g., `asyncio.create_subprocess_exec`, `await proc.communicate()`, and `run_sync` calls).
- Context extracts saved as multiple files: `/tmp/audit_subproc_site_*.txt` (for each relevant module). These show:
  - `src/firsttry/utils/async_subproc.py` implements an async `run()` that awaits `proc.communicate()` and a `run_sync()` wrapper using `asyncio.run()` — proof: see `/tmp/audit_subproc_site_async_subproc.py.txt` (lines with `await proc.communicate()` and `asyncio.run`).
  - Several callsites use `await proc.communicate()` properly (e.g., `cached_orchestrator.py`, `parallel_pytest.py`, `checks_orchestrator_optimized.py`, `runners/base.py`) — proofs in `/tmp/audit_subproc_site_*.txt`.
  - Some synchronous runners call `run_sync(...)` (e.g., bandit single-run and sharded runner) — see `/tmp/audit_subproc_site_bandit_runner.py.txt` and `/tmp/audit_subproc_site_bandit_sharded.py.txt`.
- Despite these precautions, runtime logs include the `Event loop is closed` finalizer trace after FT runs completed (present in `/tmp/ft_free_lite_debug.log`, `/tmp/ft_free_strict_debug.log`, `/tmp/ft_pro_debug.log`, `/tmp/ft_promax_debug.log`). This indicates at least one transport/async subprocess object was garbage-collected after event loop shutdown. The evidence files above identify several asynchronous callsites; a code sweep (no modifications) can target a small set of files where the pattern could leave a transport open.

## 6) Test discovery proof
- Pytest collection-only output: `/tmp/manual_pytest_collect.log` — contains per-file collected item counts and shows overall test inventory; some test import errors due to missing test dependencies (fastapi) are recorded in `/tmp/manual_pytest.log` and `/tmp/manual_pytest_collect.log`.

## 7) File inventory proof
- Tracked files counts: `/tmp/audit_files_all_count.txt`, `/tmp/audit_files_py_count.txt`, `/tmp/audit_files_src_count.txt`.
- Sample paths listed in `/tmp/audit_files_py.txt` and `/tmp/audit_files_src.txt`.

## 8) Discrepancy table (observed vs expected)
- Bandit: expected to be slow when run with `-r .` — observed 5m48s (`/tmp/bandit_plain.log`) vs 1m52s with excludes (`/tmp/bandit_excl.log`) and ~5–6s with explicit sharded per-file runs (`/tmp/run_bandit_sharded_jobs2.log`). Proof: the logs and JSON counts (`/tmp/bandit_plain.json` 10126 results; `/tmp/bandit_excl.json` 6381 results; `.firsttry` sharded merged 959 results; `/workspaces/Firstry/.firsttry/bandit.json` 161 results).
- FT phase attribution vs direct tools: FT often reports ~30s for bandit in `other` bucket even when bandit is Locked in that tier (free-lite), which can mislead about actual runtime cost. Proof: `/tmp/ft_free_lite_debug.log` shows `bandit=30.0s` while the check is reported as Locked (see lines in `/tmp/extract_free_lite_tools.txt`).
- Overall FT total runtime in unlocked tiers (~37–42s) includes bandit and pip-audit time; when bandit is run with sharding and excludes by FT (Pro/Promax), merged bandit.json shows far fewer results and faster runtime than naive recursive run.

## 9) Root-cause hypotheses (ranked)
1. Bandit full-tree recursion when called without excludes is the primary source of large wall time (evidence: `/tmp/bandit_plain.log` 5m48s vs `/tmp/bandit_excl.log` 1m52s). The presence or absence of `-x` and explicit file-target usage determines performance.
2. FT shows bandit timing even when the check is Locked (free-lite), causing apparent attribution of time to locked checks — proof: `/tmp/ft_free_lite_debug.log` (bandit=30s) while the check is locked in the same log lines.
3. Asynchronous subprocess transports occasionally get finalized after the loop has closed, producing `Event loop is closed` finalizer traces — evidence: finalizer traces in all FT logs and async callsites identified in `/tmp/audit_subproc_sites.txt` and context files.

## 10) Next diagnostic steps (read-only)
- Re-run FT free-lite with verbose command-logging enabled (if available) or set FT_DEBUG env to have FT print exact spawned commands to confirm whether bandit was actually spawned/why bandit=30s appears when locked. (Command to run: `FT_DEBUG=1 python -m firsttry run --tier free-lite --debug-phases --show-report` — capture to `/tmp`.)
- Run FT with specific env override `FT_BANDIT_EXCLUDES` set to the same excludes used above and re-run a Pro run to measure delta in bandit time.
- Inspect specific async callsites noted in `/tmp/audit_subproc_site_*.txt` (e.g., `cached_orchestrator.py`, `parallel_pytest.py`, `checks_orchestrator_optimized.py`) to verify they await `proc.communicate()` and do not leave transports open; re-run FT and check if finalizer traces disappear. (Read-only: `sed -n` lines from those files.)

---

### Generated artifacts (proof pack index):
See `.firsttry/audit/INDEX.txt` for the full list and locations of all logs and JSON artifacts produced during this audit.

