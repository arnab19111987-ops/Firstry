#!/usr/bin/env bash
set -euo pipefail

echo "== Verify: import path =="
python - <<'PY'
import importlib, sys
print("python:", sys.version)
m = importlib.import_module("firsttry.license_guard")
print("get_current_tier exists:", hasattr(m, "get_current_tier"))
print("require_pro exists:", hasattr(m, "require_pro"))
PY

echo
echo "== Verify: demo key forces pro =="
unset FIRSTTRY_LICENSE_KEY || true
export FIRSTTRY_DEMO_MODE=1
python - <<'PY'
from firsttry.license_guard import get_current_tier, tier_is_pro
print("tier:", get_current_tier(), "is_pro:", tier_is_pro())
PY

echo
echo "== Verify: pro gate blocks when not pro =="
unset FIRSTTRY_DEMO_MODE || true
unset FIRSTTRY_LICENSE_KEY || true
python - <<'PY'
from firsttry.license_guard import require_pro
try:
    require_pro("ft doctor")
    print("UNEXPECTED: gate did not block")
except SystemExit as e:
    print("blocked with exit", e.code)
PY

echo
echo "== Verify: CLI handlers call require_pro =="
python - <<'PY'
import inspect
import firsttry.cli as cli
print("cmd_doctor exists:", hasattr(cli, "cmd_doctor"))
print("cmd_mirror_ci exists:", hasattr(cli, "cmd_mirror_ci"))
src = inspect.getsource(cli.cmd_doctor)
print("require_pro in cmd_doctor:", "require_pro(" in src)
src2 = inspect.getsource(cli.cmd_mirror_ci)
print("require_pro in cmd_mirror_ci:", "require_pro(" in src2)
PY

echo
echo "== Verify: planner VIP hook toggles by tier =="
python - <<'PY'
import os
from types import SimpleNamespace
try:
    from firsttry.planner.dag import maybe_apply_team_intel
except Exception:
    print("planner hook missing"); raise
class Plan(SimpleNamespace):
    def __init__(self): self.collected=[]
    def add_tests(self, ids): self.collected.extend(ids)
p=Plan(); os.environ.pop("FIRSTTRY_DEMO_MODE", None)
maybe_apply_team_intel(p); print("free collected:", p.collected)
os.environ["FIRSTTRY_DEMO_MODE"]="1"
p2=Plan(); maybe_apply_team_intel(p2); print("pro collected:", p2.collected)
PY

echo
echo "== Verify: cache selection promotes S3 only for pro =="
python - <<'PY'
import os
from firsttry import run_swarm
try:
    get_caches = getattr(run_swarm, 'get_caches_for_run')
except Exception:
    # older API: call run_swarm.get_caches_for_run if present
    get_caches = getattr(run_swarm, 'get_caches_for_run', None)
if get_caches is None:
    print('get_caches_for_run not present')
else:
    os.environ.pop("FIRSTTRY_DEMO_MODE", None)
    c = get_caches()
    print("free caches:", [type(x).__name__ for x in c])
    os.environ["FIRSTTRY_DEMO_MODE"]="1"
    os.environ["FT_S3_BUCKET"]="demo-bucket"
    c2 = get_caches()
    print("pro caches:", [type(x).__name__ for x in c2])
PY

echo
echo "✅ All smoke checks ran."
