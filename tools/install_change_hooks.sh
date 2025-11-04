#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
HOOKS="${ROOT}/.git/hooks"
LOGGER_REL="tools/change_logger.sh"   # referenced from repo root

install_hook() {
  local name="$1" mode="$2"
  local target="${HOOKS}/${name}"

  # Backup existing hook if it exists and isn't ours
  if [ -f "$target" ] && ! grep -q "$LOGGER_REL" "$target"; then
    cp -f "$target" "${target}.bak"
    echo "Backed up existing hook to ${target}.bak"
  fi

  cat > "$target" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
# Always run from repo root, regardless of caller CWD
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"
MODE_PLACEHOLDER
bash "$ROOT/LOGGER_PLACEHOLDER" "$MODE" || true
EOF

  # Inject mode and logger path safely
  sed -i.bak "s|MODE_PLACEHOLDER|MODE=\"$mode\"|g" "$target"
  sed -i.bak "s|LOGGER_PLACEHOLDER|$LOGGER_REL|g" "$target"
  rm -f "${target}.bak"

  chmod +x "$target"
  echo "Installed .git/hooks/${name}"
}

install_hook "pre-commit"   "precommit"
install_hook "post-commit"  "commit"
install_hook "post-merge"   "merge"
install_hook "post-rewrite" "rewrite"
install_hook "pre-push"     "push"

echo "All hooks installed."
