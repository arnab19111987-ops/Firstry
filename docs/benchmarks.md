# Benchmarks — FirstTry vs Manual

This folder contains a reproducible benchmarking kit to compare FirstTry CLI scenarios against manual developer commands.

Location
- Tools: `tools/bench/*`
- Outputs: `.firsttry/bench/` (raw JSONL under `raw/`, aggregated `report.md` and `summary.csv`)

Quick start

1. Fast run (one trial per cell):

```bash
make bench-fast
```

2. Full run (default 3 trials per cell):

```bash
make bench
```

What is measured
- Wall-clock (real), user, and sys seconds.
- Cold: caches removed before each trial.
- Warm: first run warms caches; subsequent trials measured.
- Each trial records tool versions, git SHA and CPU count.

Interpreting results
- `.firsttry/bench/report.md` contains a human-readable summary with a comparison table (median times and speedups).
- `.firsttry/bench/summary.csv` contains numeric aggregates for downstream analysis.

Customization
- To add or modify scenarios, edit `tools/bench/bench_run.sh` (manual command mapping).
- To change trial count: set `TRIALS=N` environment variable when calling the scripts or use `make bench-fast`.

CI note
- A workflow can be added to run a fast bench on demand (workflow_dispatch) and upload `.firsttry/bench/` as an artifact. Keep bench runs out of the default PR gates because they are noisy and environment-dependent.
