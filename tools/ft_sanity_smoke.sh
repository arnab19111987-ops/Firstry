
#!/usr/bin/env bash
set -euo pipefail

# Simple sanity runner for FirstTry core features.
# Usage: bash tools/ft_sanity_smoke.sh

# ---- helpers ----

section() {
  echo
  echo "================================================================"
  echo "== $1 =="
  echo "================================================================"
}

must_succeed() {
  local label="$1"
  shift
  section "$label"
  echo "+ $*"
  "$@"
  echo "-- OK: $label"
}

optional_check() {
  local label="$1"
  shift
  section "$label (optional)"
  echo "+ $*"
  if "$@" ; then
    echo "-- OK: $label"
  else
    echo "-- SKIP/FAIL (non-fatal): $label"
  fi
}

# ---- repo & env guardrails ----

if [ ! -f "pyproject.toml" ] && [ ! -d "src/firsttry" ]; then
  echo "ERROR: Run this from the FirstTry repo root (pyproject.toml / src/firsttry not found)."
  exit 1
fi

# Keep runs deterministic / safe-ish.
export FT_SEND_TELEMETRY=${FT_SEND_TELEMETRY:-0}
export FT_DISABLE_AUTO_PARITY=${FT_DISABLE_AUTO_PARITY:-1}
export FIRSTTRY_SHARED_SECRET=${FIRSTTRY_SHARED_SECRET:-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa}

echo "Using env:"
echo "  FT_SEND_TELEMETRY=$FT_SEND_TELEMETRY"
echo "  FT_DISABLE_AUTO_PARITY=$FT_DISABLE_AUTO_PARITY"
echo "  FIRSTTRY_SHARED_SECRET=${FIRSTTRY_SHARED_SECRET:0:4}****"

# ---- core CLI surface ----

must_succeed "CLI help" ft --help >/dev/null
must_succeed "CLI version" ft --version

# ---- main user flows (tiers) ----
# These are the big promises to users.

must_succeed "Strict tier (ft run strict)" ft run strict
must_succeed "Fast tier (ft run fast)"     ft run fast

# If you have other tiers you consider public, you can add:
# optional_check "Pro tier surface" ft run pro --help >/dev/null

# ---- CI mirror ----

# Mirror-CI can be very verbose; we just care that it completes with rc=0.
must_succeed "Mirror CI on this repo" ft mirror-ci >/dev/null

# ---- auxiliary commands (only if present) ----

# Doctor / diagnostics, if implemented:
optional_check "Doctor CLI surface" ft doctor --help >/dev/null || true

# If you later add a top-level cache / config command:
# optional_check "Cache CLI surface" ft cache --help >/dev/null || true
# optional_check "Config CLI surface" ft config --help >/dev/null || true

echo
echo "================================================================"
echo "FirstTry sanity smoke: COMPLETED"
echo "================================================================"
