#!/usr/bin/env bash
set -euo pipefail
# bench_matrix.sh
# Run the full bench matrix: scenarios x modes x toolchains

TRIALS=${TRIALS:-3}
# use a bench-specific output dir to avoid being removed by cold-mode cleanup
OUTDIR=${OUTDIR:-.firsttry_bench/bench/raw}
mkdir -p "$OUTDIR"

SCENARIOS=(lite strict pro promax)
MODES=(cold warm)
TOOLCHAINS=(ft manual)

for scenario in "${SCENARIOS[@]}"; do
  for mode in "${MODES[@]}"; do
    for tc in "${TOOLCHAINS[@]}"; do
      echo "=== Cell: $scenario | $mode | $tc ==="
      # run warmup for warm mode: bench_run handles warm-up on trial 1
  SCENARIO=$scenario MODE=$mode TOOLCHAIN=$tc TRIALS=$TRIALS OUTDIR="$OUTDIR" bash tools/bench/bench_run.sh
    done
  done
done

echo "All raw results written to $OUTDIR"
