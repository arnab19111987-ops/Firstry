#!/usr/bin/env bash
set -euo pipefail

# Always operate from the repo root if available (hooks can run from odd CWDs)
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

LOG_DIR=".firsttry/change_log"
mkdir -p "$LOG_DIR"

now() { date +"%Y-%m-%dT%H-%M-%S"; }
sha_short() { git rev-parse --short HEAD 2>/dev/null || echo "NOHEAD"; }
branch() { git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "DETACHED"; }
upstream() { git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>/dev/null || echo "none"; }
author() { git config user.name 2>/dev/null || echo "unknown"; }
email() { git config user.email 2>/dev/null || echo "unknown@example.com"; }

# mode: commit|precommit|merge|rewrite|push|manual
MODE="${1:-manual}"
EXTRA_TITLE="${2:-}"

TS="$(now)"
HEAD_SHA="$(sha_short)"
BRANCH="$(branch)"
UPSTREAM="$(upstream)"
AUTHOR="$(author)"
EMAIL="$(email)"

FILENAME_PREFIX="${TS}_${MODE}"
[ "$MODE" = "commit" ] && FILENAME_PREFIX="${TS}_${MODE}_${HEAD_SHA}"
OUT="${LOG_DIR}/${FILENAME_PREFIX}.md"

# Summaries
GIT_FILES_SUMMARY="$(git status --porcelain=v1 2>/dev/null || true)"
STAGED_COUNT="$(git diff --cached --name-only | wc -l | tr -d ' ' || true)"
WORKING_COUNT="$(git diff --name-only | wc -l | tr -d ' ' || true)"
UNTRACKED_COUNT="$(git ls-files --others --exclude-standard | wc -l | tr -d ' ' || true)"

# Safe diffstat (exclude huge folders); use `--` before pathspecs
EXCLUDES=( ":^node_modules" ":^.next" ":^dist" ":^build" ":^venv" ":^.venv" )
DIFFSTAT_STAGED="$(git diff --cached --stat -- "${EXCLUDES[@]}" 2>/dev/null || true)"
DIFFSTAT_WORKING="$(git diff --stat -- "${EXCLUDES[@]}" 2>/dev/null || true)"

# Largest edits by lines changed; use tab FS (numstat is tab-separated)
TOPN=15
TOP_LARGEST="$(git diff --numstat -- "${EXCLUDES[@]}" 2>/dev/null \
  | awk -F'\t' '{print ($1+$2) "\t" $3}' \
  | sort -nr \
  | head -n "$TOPN" \
  || true)"

# Optional FirstTry summary (fast + non-breaking). We only read a prior report by default.
FT_BIN="$(command -v ft || true)"
FT_SUMMARY=""
if [ -n "$FT_BIN" ] && [ -f ".firsttry/report.json" ]; then
  FT_SUMMARY="$("$FT_BIN" lock 2>/dev/null || true)"
fi

cat > "$OUT" <<EOF
# Change Snapshot — ${MODE} ${EXTRA_TITLE}

- Timestamp: ${TS}
- Branch: ${BRANCH}
- HEAD: ${HEAD_SHA}
- Upstream: ${UPSTREAM}
- Author: ${AUTHOR} <${EMAIL}>

## Counts
- Staged files: ${STAGED_COUNT}
- Working (modified but unstaged): ${WORKING_COUNT}
- Untracked: ${UNTRACKED_COUNT}

## Staged diffstat
\`\`\`
${DIFFSTAT_STAGED}
\`\`\`

## Working diffstat
\`\`\`
${DIFFSTAT_WORKING}
\`\`\`

## Largest edits (by lines +/-)
\`\`\`
${TOP_LARGEST}
\`\`\`

## git status (porcelain)
\`\`\`
${GIT_FILES_SUMMARY}
\`\`\`

$( [ -n "$FT_SUMMARY" ] && printf "## FirstTry lock summary\n\`\`\`\n%s\n\`\`\`\n" "$FT_SUMMARY" )
EOF

echo "Wrote ${OUT}"

exit 0
