#!/usr/bin/env bash
set -euo pipefail

export FT_FORCE_REPORT_WRITE=1
python -m firsttry run --tier free-lite --debug-phases --show-report \
  --report-json .firsttry/smoke_report.json 2>&1 | tee .firsttry/ft_smoke.log

pytest -q tests/test_ft_smoke.py tests/test_report_meta.py
