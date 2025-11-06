# FT vs Manual — Tier `lite`

| Tool | Manual (s) | Manual errors | FT (ms, warm) | FT status | Cache | FT errors | Speedup× | Parity |
|---|---:|---:|---:|:--:|:--:|---:|---:|:--:|
| ruff | 0.01178 | 3 | 8 | ok | hit-local | 0 | 1.47 | DIFF(man=3, ft=0) |
| mypy | 0.838714 | 142 | 1022 | fail | miss-run | 142 | 0.82 | OK |
| pytest | 0.645097 | 0 | 405 | ok | miss-run | 0 | 1.59 | OK |
| bandit | 5.441442 | 152 |  |  |  |  |  |  |