#!/usr/bin/env bash
set -euo pipefail

# scripts/ft_gap_probe_telemetry.sh
# Read-only probe for telemetry behavior. Idempotent: always overwrites the single log file.

LOG_DIR=".firsttry/copilot/logs"
LOG_FILE="$LOG_DIR/telemetry_probe.log"
mkdir -p "$LOG_DIR"
: > "$LOG_FILE"

echo "Telemetry probe started at $(date --utc +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG_FILE"

# 1) List source files mentioning telemetry (case-insensitive)
echo "\n=== Files mentioning 'telemetry' (case-insensitive) ===" >> "$LOG_FILE"
grep -RIn --line-number "telemetry" src/firsttry || true >> "$LOG_FILE"

# 2) Grep for environment variable-like tokens that contain TELEMETRY in source
echo "\n=== Potential telemetry-related ENV VARS (tokens with TELEMETRY) ===" >> "$LOG_FILE"
# extract likely env-var names used in source - uppercase tokens with TELEMETRY
grep -RIn --line-number -oE "\b[A-Z0-9_]{3,}TELEMETRY[A-Z0-9_]*\b" src/firsttry || true
# Save unique list to log
grep -RIn --line-number -oE "\b[A-Z0-9_]{3,}TELEMETRY[A-Z0-9_]*\b" src/firsttry | sort -u >> "$LOG_FILE" || true

# 3) Inspect telemetry.py for default endpoints, hosts, or URLs
TELEMETRY_PY="src/firsttry/telemetry.py"
echo "\n=== telemetry.py existence ===" >> "$LOG_FILE"
if [ -f "$TELEMETRY_PY" ]; then
  echo "Found $TELEMETRY_PY" >> "$LOG_FILE"
  echo "\n--- telemetry.py contents (contextual grep for http/https/endpoint/url/host) ---" >> "$LOG_FILE"
  # Look for explicit URLs
  grep -Eno "https?://[^\"'\)\s]+" "$TELEMETRY_PY" | sed -n '1,200p' >> "$LOG_FILE" || true
  # Look for keywords endpoint, url, host
  grep -In --line-number -E "endpoint|url|host|collector|telemetry|ingest|send_report|report_url|telemetry_endpoint" "$TELEMETRY_PY" >> "$LOG_FILE" || true
  # Look for network libraries in telemetry.py
  grep -In --line-number -E "requests|httpx|urllib|aiohttp|socket|httplib|urllib3|fetch" "$TELEMETRY_PY" >> "$LOG_FILE" || true
else
  echo "$TELEMETRY_PY not present" >> "$LOG_FILE"
fi

# 4) Grep for any uses of network-related libraries in modules mentioning telemetry
echo "\n=== Network-library usage in telemetry-related modules (search src/firsttry for telemetry keyword then grep libraries) ===" >> "$LOG_FILE"
# find files that mention telemetry and then scan them for network libs
files=$(grep -RIl "telemetry" src/firsttry || true)
if [ -n "$files" ]; then
  for f in $files; do
    echo "\n-- File: $f --" >> "$LOG_FILE"
    grep -In --line-number -E "requests|httpx|urllib|aiohttp|socket|httplib|urllib3|fetch" "$f" >> "$LOG_FILE" || true
  done
else
  echo "No files with 'telemetry' keyword found; scanning telemetry.py and all src/firsttry for network libs" >> "$LOG_FILE"
  grep -RIn --line-number -E "requests|httpx|urllib|aiohttp|socket|httplib|urllib3|fetch" src/firsttry || true >> "$LOG_FILE"
fi

# 5) Grep the whole src for obvious telemetry opt-in/opt-out flags
echo "\n=== Telemetry opt-in/out keywords across src/firsttry ===" >> "$LOG_FILE"
grep -RIn --line-number -E "ENABLE_TELEMETRY|DISABLE_TELEMETRY|SEND_TELEMETRY|TELEMETRY_ENABLED|OPT[_-]?IN|OPT[_-]?OUT|ALLOW_TELEMETRY|FIRSTTRY_TELEMETRY|FIRSTTRY_SEND_TELEMETRY|FIRSTTRY_DISABLE_TELEMETRY" src/firsttry || true >> "$LOG_FILE"

# 6) Extract candidate ENV var names from all src files (tokens in all caps with underscores)
echo "\n=== Candidate ENV VAR TOKENS (all caps tokens) ===" >> "$LOG_FILE"
# heuristic: capture ALL-uppercase underscore tokens (likely env vars) that include TELEMETRY or FIRSTTRY
grep -RIn --line-number -oE "\b[A-Z0-9_]{3,}\b" src/firsttry | sort -u | grep -E "FIRSTTRY|TELEMETRY|TELEMETRY_ENABLED|DISABLE" | sed -n '1,200p' >> "$LOG_FILE" || true

# Heuristic decisions for JSON summary
uses_network="unknown"
opt_in="unknown"
opt_out_env_vars="[]"

# If telemetry.py has explicit http:// or https:// occurrences -> uses_network=true
if [ -f "$TELEMETRY_PY" ] && grep -Eno "https?://[^\"'\)\s]+" "$TELEMETRY_PY" | grep -q .; then
  uses_network="true"
fi

# If network libraries appear in telemetry.py or telemetry-related files -> uses_network=true
if grep -RIn --line-number -E "requests|httpx|urllib|aiohttp|socket|httplib|urllib3|fetch" src/firsttry | grep -q .; then
  uses_network="true"
fi

# If no network libraries and no URLs found, be conservative: set unknown if telemetry.py absent else false
if [ "$uses_network" = "unknown" ]; then
  if [ -f "$TELEMETRY_PY" ]; then
    # telemetry.py exists but no URLs/libraries found -> might be offline-only
    uses_network="unknown"
  else
    uses_network="unknown"
  fi
fi

# Determine opt-in / opt-out heuristics
# If we find a DISABLE or DISABLE_TELEMETRY env var, mark opt_in=false
disable_vars=$(grep -RIn --line-number -oE "\b[A-Z0-9_]{3,}DISABLE[A-Z0-9_]*TELEMETRY[A-Z0-9_]*\b|\bFIRSTTRY_DISABLE_TELEMETRY\b" src/firsttry || true)
if [ -n "$disable_vars" ]; then
  opt_in="false"
  # collect env var names
  vars=$(echo "$disable_vars" | sed -n 's/.*:\([A-Z0-9_]*\)/\1/p' | sort -u | tr '\n' ',' | sed 's/,$//')
  if [ -n "$vars" ]; then
    opt_out_env_vars="[$(echo "$vars" | tr ',' '\n' | sed 's/^/"/' | sed 's/$/"/' | paste -sd, -)]"
  fi
fi

# If we find ENABLE_TELEMETRY or SEND_TELEMETRY -> opt_in=true
enable_vars=$(grep -RIn --line-number -E "ENABLE_TELEMETRY|SEND_TELEMETRY|TELEMETRY_ENABLED|FIRSTTRY_SEND_TELEMETRY" src/firsttry || true)
if [ -n "$enable_vars" ] && [ "$opt_in" = "unknown" ]; then
  opt_in="true"
  # collect env var names
  vars2=$(echo "$enable_vars" | sed -n 's/.*:\([A-Z0-9_]*\)/\1/p' | sort -u | tr '\n' ',' | sed 's/,$//')
  if [ -n "$vars2" ]; then
    # merge into opt_out_env_vars if any
    if [ "$opt_out_env_vars" = "[]" ]; then
      opt_out_env_vars="[$(echo "$vars2" | tr ',' '\n' | sed 's/^/"/' | sed 's/$/"/' | paste -sd, -)]"
    else
      opt_out_env_vars="$opt_out_env_vars,$(echo "$vars2" | tr ',' '\n' | sed 's/^/"/' | sed 's/$/"/' | paste -sd, -)"
    fi
  fi
fi

# Final adjustments: if opt_out_env_vars still empty, make it []
if [ -z "$opt_out_env_vars" ] || [ "$opt_out_env_vars" = "" ]; then
  opt_out_env_vars="[]"
fi

# Print JSON summary to stdout
jq -n --arg uses_network "$uses_network" --arg opt_in "$opt_in" --argjson opt_out_env_vars "$opt_out_env_vars" '{uses_network: ($uses_network), opt_in: ($opt_in), opt_out_env_vars: $opt_out_env_vars}'

# Also print a brief tail of the log for convenience
echo "\n--- telemetry_probe.log (tail) ---"
tail -n 200 "$LOG_FILE" || true

exit 0
