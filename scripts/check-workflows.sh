#!/usr/bin/env bash
set -euo pipefail

DIR=".github/workflows"
[ -d "$DIR" ] || exit 0

fail=0

# 1) Block deprecated artifact action v3
# Exclude audit workflow which self-documents checks
if grep -RInq --exclude='audit.yml' --include='*.yml' 'actions/upload-artifact@v3' "$DIR"; then
  echo "❌ Found deprecated actions/upload-artifact@v3 in workflows. Use @v4 or @v5."
  grep -RIn --include='*.yml' 'actions/upload-artifact@v3' "$DIR" || true
  fail=1
fi

# 2) Optionally block raw SHA pins for actions (7+ hex); comment out if your org requires SHAs.
if grep -RInq --exclude='audit.yml' --include='*.yml' 'uses: .\+@[0-9a-fA-F]\{7,\}' "$DIR"; then
  echo "⚠️  Found SHA-pinned actions. Prefer majors like @v4/@v5 unless org policy requires SHAs."
  grep -RIn --include='*.yml' 'uses: .\+@[0-9a-fA-F]\{7,\}' "$DIR" || true
  # fail=1  # enable to make it a hard failure
fi

# 3) Nudge to current majors
if grep -RInq --exclude='audit.yml' --include='*.yml' 'actions/checkout@v[0-3]\b' "$DIR"; then
  echo "❌ actions/checkout should be @v4"
  grep -RIn --include='*.yml' 'actions/checkout@v[0-3]\b' "$DIR" || true
  fail=1
fi

if grep -RInq --exclude='audit.yml' --include='*.yml' 'actions/setup-python@v[0-4]\b' "$DIR"; then
  echo "❌ actions/setup-python should be @v5"
  grep -RIn --include='*.yml' 'actions/setup-python@v[0-4]\b' "$DIR" || true
  fail=1
fi

# 4) Deprecated ::set-output
if grep -RInq --exclude='audit.yml' --include='*.yml' '::set-output' "$DIR"; then
  echo "❌ Deprecated '::set-output' detected. Use \$GITHUB_OUTPUT."
  grep -RIn --exclude='audit.yml' --include='*.yml' '::set-output' "$DIR" || true
  fail=1
fi

exit $fail
