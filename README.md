## Fast operational proof

This repository includes a small demo tier (`free-fast`) that runs a known-clean
Python file and a tiny test so you can exercise cold→warm caching quickly.

Run the built Make helper to execute a cold then warm run and print the
report + history summary:

```bash
![License: FSAL 1.0](https://img.shields.io/badge/license-FSAL%201.0-blue) ![Public Source](https://img.shields.io/badge/source-available-green)

## License

FirstTry is source-available under the FirstTry Source-Available License (FSAL 1.0).

You may read, clone, study, and modify the code for personal or internal use.

Commercial use, redistribution, hosting, or competing offerings are prohibited without a paid license.

# FirstTry

FirstTry is a local CI mirror and progressive CI runner that helps developers run CI-style checks (ruff, mypy, pytest, etc.) locally with caching and tiered profiles so you can verify code will pass CI before pushing.

## Install

Install from PyPI (package name: `firsttry-run`):

```bash
pip install firsttry-run
```

For development:

```bash
python -m pip install -e ".[dev]"
```

## Quick start

From your project root:

```bash
ft run fast     # quick checks on changed files
ft run strict   # full strict tier checks
```

`ft` and `firsttry` both map to the same CLI entrypoint (`firsttry.cli:main`).

## Tiers

- `fast`: lightweight checks (linters on changed files, smoke pytest).
- `strict`: full linters, type checks, and a broader pytest selection.
- `pro` / `enterprise`: (if enabled) add remote cache integrations, S3, and enterprise-only checks.

See `docs/` for details on tier configuration and how to add custom profiles.

## Demo / Benchmarks

This repo includes a small demo tier (`free-fast`) to exercise cold→warm caching quickly:

```bash
make ft-proof
```

The demo runs a tiny sample and prints a proof report. See `.github/workflows/firsttry-proof.yml` for an example CI hook.

## Telemetry

FirstTry includes a small telemetry sender.
See `TELEMETRY.md` for details and how to opt in/out. The CLI also writes local telemetry status to `.firsttry/telemetry_status.json`.

## License

This project is distributed under the FirstTry Source-Available License (FSAL 1.0). See `LICENSE` for full terms.
- **Opt-out**: set `FT_SEND_TELEMETRY=0`

