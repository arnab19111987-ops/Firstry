(# Firstry)

![verify-bandit](https://github.com/arnab19111987-ops/Firstry/actions/workflows/verify-bandit.yml/badge.svg)

## Security (Bandit) — Advisory by Policy

- CI: `verify-bandit` runs FirstTry Pro and respects our policy (`blocking = false` by default).
- Local mirror: `make ci-bandit`
- Quick smoke: `./tools/verify_bandit_advisory.sh`
- Reports: check `.firsttry/pro.json` (and `.firsttry/bandit.json` if present).

Please see `docs/config.md` for Bandit configuration and policy details.

