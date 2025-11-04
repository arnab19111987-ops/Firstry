#!/usr/bin/env bash
set -euo pipefail
ft pro --report-json .firsttry/pro.json --show-report || true
python - <<'PY'
import json,sys
r=json.load(open(".firsttry/pro.json"))
bandit=[c for c in r.get("checks",[]) if c.get("id")=="bandit" or c.get("name")=="bandit"]
if not bandit: print("bandit missing"); sys.exit(2)
b=bandit[0]; s=b.get("summary",{}); blocking=b.get("blocking",True); high=s.get("high",0)
print(f"Bandit: blocking={blocking}, high={high}")
print("PASS (advisory respected)" if not(blocking and high>0) else "FAIL")
sys.exit(0 if not(blocking and high>0) else 1)
PY
