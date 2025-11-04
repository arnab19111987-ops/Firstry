#!/usr/bin/env bash
set -euo pipefail

export FT_FORCE_REPORT_WRITE=1
python -m firsttry run --tier free-lite --debug-phases --show-report \
  --report-json .firsttry/smoke_report.json 2>&1 | tee ft_smoke.log

echo "Artifacts ready:
  - ft_smoke.log
  - .firsttry/smoke_report.json
"
