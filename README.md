(# Firstry)

![verify-bandit](https://github.com/arnab19111987-ops/Firstry/actions/workflows/verify-bandit.yml/badge.svg)

## Security (Bandit) — Advisory by Policy


Please see `docs/config.md` for Bandit configuration and policy details.
```markdown
(# Firstry)

![verify-bandit](https://github.com/arnab19111987-ops/Firstry/actions/workflows/verify-bandit.yml/badge.svg)

## Security (Bandit) — Advisory by Policy

- CI: `verify-bandit` runs FirstTry Pro and respects our policy (`blocking = false` by default).
- Local mirror: `make ci-bandit`
- Quick smoke: `./tools/verify_bandit_advisory.sh`
- Reports: check `.firsttry/pro.json` (and `.firsttry/bandit.json` if present).

Please see `docs/config.md` for Bandit configuration and policy details.

```

### Performance & Controls

- `FT_BANDIT_JOBS` – override Bandit shard count (env > config > CPU). Example: `FT_BANDIT_JOBS=4`.
- `FT_FAST_FAIL=1` – Pytest fast-fail during local dev (adds `-q --maxfail=1 -x`). Off by default.
- `FT_FORCE_REPORT_WRITE=1` – force blocking, atomic report writes (CI/tests only).
- Caches: FirstTry never deletes `.ruff_cache`, `.mypy_cache`, `.pytest_cache` during normal runs.

These knobs help keep local runs snappy while allowing CI to enforce deterministic artifacts and performance thresholds.

Quick check

Run the CI-equivalent smoke locally with deterministic output:

```bash
bash tools/ci_smoke.sh
```

Perf visibility:

```bash
jq '.meta' .firsttry/smoke_report.json
```

Shard sanity (debug):

```bash
FT_BANDIT_JOBS=4 python -m firsttry run --tier pro --debug-phases --show-report
```

Fast-path expectations (approx):

On a 2-CPU dev box, Free-Lite warm runs should be ~1–3s. Pro bandit time scales with tracked .py files; the CI workflow asserts conservative thresholds by default.

