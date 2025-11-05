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

