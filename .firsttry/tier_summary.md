# FirstTry Tier Summary

## free-lite

- Cold: p50=180ms, p95=354ms, ok=2/2
- Warm: p50=182ms, p95=357ms, ok=2/2, cache_hit_rate=0.5
- Slowest warm checks:
  - pytest:_root: 357ms (miss-run)
  - ruff:_root: 7ms (hit-local)

## lite

- Cold: p50=401ms, p95=1028ms, ok=2/3
- Warm: p50=384ms, p95=1010ms, ok=2/3, cache_hit_rate=0.3333333333333333
- Slowest warm checks:
  - mypy:_root: 1010ms (miss-run)
  - pytest:_root: 384ms (miss-run)
  - ruff:_root: 7ms (hit-local)
