#!/usr/bin/env bash
set -euo pipefail

fail=0
files=$(ls .github/workflows/*.yml 2>/dev/null || true)
[ -z "$files" ] && exit 0

bad_art=$(grep -R --line-number -E 'uses:\s*actions/upload-artifact@v3' .github/workflows || true)
if [ -n "$bad_art" ]; then echo "[ft] deprecated upload-artifact@v3:"; echo "$bad_art"; fail=1; fi

bad_sha=$(grep -R --line-number -E 'uses:\s*[^ ]+@[0-9a-f]{7,}' .github/workflows | grep -vE 'checkout@v4|setup-python@v5|upload-artifact@v4' || true)
if [ -n "$bad_sha" ]; then echo "[ft] raw SHA-pinned actions:"; echo "$bad_sha"; fi  # set fail=1 if your policy forbids SHA pins

bad_out=$(grep -R --line-number -E '::set-output' .github/workflows | grep -v 'audit.yml' || true)
if [ -n "$bad_out" ]; then echo "[ft] deprecated ::set-output usage:"; echo "$bad_out"; fail=1; fi

exit $fail
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
