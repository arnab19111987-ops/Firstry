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

See the full terms in `LICENSE`.

## FAQ — Why Source Available?

Is FirstTry open-source?

No. FirstTry is source-available. You can read and modify the code, but commercial use is restricted.

Can I use it at work?

Yes — for evaluation or personal use. Production/team/company use requires a paid license.

Can I fork it?

Yes, privately. No, you cannot fork and publish or redistribute.

Can I build my own version?

Yes, but you cannot release, sell, or host it.

Why not MIT/Apache?

Because:

- Competitors can steal the code

- Enterprises lose trust if the project dies

- Sustaining a dev tool requires revenue

This model is used by Elastic, Redis, Hashicorp, Sentry, MongoDB, Vercel Turbo, and others.

## Fast operational proof

This repository includes a small demo tier (`free-fast`) that runs a known-clean
Python file and a tiny test so you can exercise cold→warm caching quickly.

Run the built Make helper to execute a cold then warm run and print the
report + history summary:

```bash
make ft-proof
```

Behavior:
- `free-fast` runs `ruff` on `src/ft_demo/math.py` (if present) and `pytest` on
	`tests/test_ok.py` (if present).
- The second run should show `cache_status: hit-local` for checks and exit `0`.

If you want this demo enabled in CI, see `.github/workflows/firsttry-proof.yml`.

## Telemetry (opt-out)

FirstTry sends **minimal, anonymized** usage metrics (e.g., command, tier, durations, success/fail) to help improve the tool.
- Endpoint: configurable via `FIRSTTRY_TELEMETRY_URL` (default internal endpoint)
- Stored locally: `.firsttry/telemetry_status.json`
- **Opt-out**: set `FT_SEND_TELEMETRY=0`

Examples:
```bash
# Disable telemetry for current shell
export FT_SEND_TELEMETRY=0

# One-off run without telemetry
FT_SEND_TELEMETRY=0 python -m firsttry run
```

