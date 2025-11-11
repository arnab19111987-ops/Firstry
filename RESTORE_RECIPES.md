# FirstTry Performance Optimization - Restore Recipes

**Quick Reference**: Complete guide for restoring your performance optimization work in any scenario.

---

## 📦 Available Bundles

### 1. **Incremental Bundle** (Recommended for most cases)
- **File**: `firsttry-perf-40pc.bundle` (106 KB)
- **Contains**: Only your 3 commits on top of origin/main
- **Requires**: Access to origin/main commit (5013d8de)
- **Use when**: Target machine can read the original repo

### 2. **Standalone Bundle** (Works anywhere)
- **File**: `firsttry-standalone.bundle` (80 MB)
- **Contains**: Complete repository history (all branches, all commits)
- **Requires**: Nothing - completely self-contained
- **Use when**: No access to original repo OR disaster recovery

---

## 🚀 Restore Recipes

### Recipe 1: Incremental Bundle (Small & Clean) ⭐ RECOMMENDED

**When to use**: Target machine can clone or has read access to the original repo.

**Steps**:
```bash
# 1. Clone the original repository
git clone https://github.com/arnab19111987-ops/Firstry.git
cd Firstry

# 2. Fetch your bundle on top of origin/main
git fetch /path/to/firsttry-perf-40pc.bundle perf/optimizations-40pc:perf/optimizations-40pc

# 3. Checkout your branch
git switch perf/optimizations-40pc

# Done! You now have all 3 commits with 40% performance improvement.
```

**Why this works**:
- Bundle contains only incremental changes (106 KB vs 80 MB)
- Git merges bundle commits with existing origin/main
- Fast and efficient

---

### Recipe 2: Standalone Bundle (Bulletproof)

**When to use**: 
- No access to original repo
- Disaster recovery scenario
- Complete isolation needed
- Air-gapped environment

**Steps**:
```bash
# 1. Clone from standalone bundle (works anywhere)
git clone /path/to/firsttry-standalone.bundle Firstry-restored
cd Firstry-restored

# 2. Switch to performance branch
git switch perf/optimizations-40pc

# Done! Complete repo with all branches and history.
```

**What you get**:
- ✅ All branches (main, perf/optimizations-40pc, and 17+ other branches)
- ✅ Complete commit history (14,505 objects)
- ✅ All remotes preserved
- ✅ No external dependencies

**To connect to origin later** (optional):
```bash
git remote add origin https://github.com/arnab19111987-ops/Firstry.git
git fetch origin
```

---

### Recipe 3: Apply Patches to Existing Repo

**When to use**:
- Already have a clone of the repo
- Want to review changes before applying
- Email/PR workflow

**Steps**:
```bash
# 1. Ensure you're on a clean main branch
cd /path/to/existing/Firstry
git checkout main
git pull origin main

# 2. Apply all patches in order
git am /path/to/patches-perf-40pc/*.patch

# Or apply individually for review:
git am /path/to/patches-perf-40pc/0001-ci-pin-upload-artifact-to-v3-across-workflows.patch
git am /path/to/patches-perf-40pc/0002-feat-Add-4-major-performance-optimizations-40-faster.patch
git am /path/to/patches-perf-40pc/0003-chore-gitignore-block-.venv-parity-and-common-artifa.patch

# Done! Patches applied as new commits on current branch.
```

**Patch details**:
- `0001-*.patch` (30 KB) - CI workflow fix
- `0002-*.patch` (2.1 MB) - Main performance optimizations
- `0003-*.patch` (57 KB) - Gitignore hardening

---

### Recipe 4: Fetch Bundle into Existing Repo

**When to use**:
- You already have a clone
- Want to add bundle as a branch without changing current work

**Steps**:
```bash
cd /path/to/existing/Firstry

# Add bundle as a remote (temporary)
git remote add perf-bundle /path/to/firsttry-perf-40pc.bundle

# Fetch the bundle
git fetch perf-bundle

# Create local branch tracking the bundle
git checkout -b perf/optimizations-40pc perf-bundle/perf/optimizations-40pc

# Optional: Remove temporary remote
git remote remove perf-bundle
```

---

### Recipe 5: Push to Personal Backup Remote

**When to use**:
- Want a hosted backup on GitHub
- Original repo blocks pushes
- Need to share via PR

**Steps**:

**A. Create repo via GitHub Web UI**:
1. Go to: https://github.com/new
2. Repository name: `firsttry-perf-backup`
3. Visibility: **Private** (recommended)
4. Click "Create repository"

**B. Push your branch**:
```bash
cd /workspaces/Firstry

# Add backup remote
git remote add backup https://github.com/arnab19111987-ops/firsttry-perf-backup.git

# Push performance branch
git push -u backup perf/optimizations-40pc

# Optional: Push all branches
git push backup --all

# Optional: Push tags
git push backup --tags
```

**C. Share via PR** (if allowed):
```bash
# Using GitHub CLI
gh pr create \
  --repo arnab19111987-ops/Firstry \
  --head arnab19111987-ops:perf/optimizations-40pc \
  --base main \
  --title "perf: 40% faster execution via 4 major optimizations" \
  --body-file BACKUP_COMPLETE_SUMMARY.md
```

---

## 🔐 Verification Before Restore

### Verify Bundle Integrity

**Incremental Bundle**:
```bash
# Check bundle structure
git bundle verify firsttry-perf-40pc.bundle

# Verify SHA256 checksum
sha256sum -c firsttry-perf-40pc.bundle.sha256
# Expected: firsttry-perf-40pc.bundle: OK

# Verify MD5 checksum
md5sum -c firsttry-perf-40pc.bundle.md5
# Expected: firsttry-perf-40pc.bundle: OK
```

**Standalone Bundle**:
```bash
# Check bundle structure
git bundle verify firsttry-standalone.bundle

# Verify SHA256 checksum
sha256sum -c firsttry-standalone.bundle.sha256
# Expected: firsttry-standalone.bundle: OK

# List all refs in bundle
git bundle list-heads firsttry-standalone.bundle
```

**Expected Checksums**:
```
Incremental Bundle:
  SHA256: e1b504e424cb06fa6a578995a83be9b741bdffbfe7240207c67a45815739d02f
  MD5:    09545e709142a1a2731195f40a0b220a

Standalone Bundle:
  SHA256: 5ffbbc19fa6a9bfeeb07ab0211128adefd7b68cbf5cc0b73ad7f11323d863c67
  MD5:    9c58a481c9dfff13ff6a164a75a80662
```

---

## 🛠️ Makefile Shortcuts

The repo includes convenient Makefile targets for backup operations:

```bash
# Create incremental backup (recreate perf-40pc bundle)
make backup

# Create standalone backup (entire repo)
make backup-standalone

# Verify all bundles
make backup-verify

# Show help
make backup-help
```

---

## 🎯 Common Scenarios

### Scenario A: Quick Team Share
**Best option**: Recipe 1 (Incremental Bundle)
```bash
# Share these files:
firsttry-perf-40pc.bundle
firsttry-perf-40pc.bundle.sha256

# Team member restores:
git clone https://github.com/arnab19111987-ops/Firstry.git
cd Firstry
git fetch /path/to/firsttry-perf-40pc.bundle perf/optimizations-40pc:perf/optimizations-40pc
git switch perf/optimizations-40pc
```

### Scenario B: Disaster Recovery
**Best option**: Recipe 2 (Standalone Bundle)
```bash
# Copy standalone bundle to safe location
# Restore anywhere, anytime:
git clone /path/to/firsttry-standalone.bundle Firstry
cd Firstry
git switch perf/optimizations-40pc
```

### Scenario C: Code Review via Email
**Best option**: Recipe 3 (Patches)
```bash
# Email all 3 patch files
# Reviewer applies:
git am *.patch
```

### Scenario D: GitHub Blocked, Need Backup
**Best option**: Recipe 5 (Backup Remote)
```bash
# Create private repo at github.com/new
git remote add backup https://github.com/<you>/firsttry-perf-backup.git
git push -u backup perf/optimizations-40pc
```

---

## 📊 What Gets Restored

After using any recipe, you'll have:

**Branch**: `perf/optimizations-40pc`

**Commits** (3 total):
1. `44cd5f27` - CI: pin upload-artifact to v3
2. `e3b0cbac` - Performance optimizations (40% faster)
3. `a631617a` - Gitignore hardening

**Performance Improvements**:
- ⚡ 40% faster execution (0.282s → 0.169s)
- 🚀 4.3x parallelization (was 2.4x)
- 📁 140 files changed (+9,016 / -7,008 lines)

**Key Files**:
- `src/firsttry/runners/fast.py` (new)
- `src/firsttry/runners/strict.py` (new)
- `src/firsttry/config_loader.py` (modified - caching)
- `src/firsttry/reports/ui.py` (modified - --no-ui flag)
- `src/firsttry/tools/ruff_tool.py` (modified - changed-file detection)
- `src/firsttry/cli.py` (modified - fast-path routing)

---

## 🔧 Troubleshooting

### Problem: "Repository lacks prerequisite commits"
**Solution**: You're using incremental bundle without origin/main. Use standalone bundle instead:
```bash
git clone /path/to/firsttry-standalone.bundle Firstry
```

### Problem: Bundle verification fails
**Solution**: Check checksums first:
```bash
sha256sum -c firsttry-perf-40pc.bundle.sha256
# If FAILED, bundle may be corrupted - request new copy
```

### Problem: Can't switch to perf/optimizations-40pc
**Solution**: Branch might have different name in bundle:
```bash
# List all branches in bundle
git bundle list-heads /path/to/bundle-file

# Fetch with explicit branch name
git fetch /path/to/bundle perf/optimizations-40pc:my-perf-branch
```

### Problem: Push to backup remote fails
**Solution**: Ensure remote repo exists and you have push access:
```bash
# Test connection
git ls-remote backup

# If fails, verify remote URL
git remote -v

# Update if needed
git remote set-url backup https://github.com/<user>/<repo>.git
```

---

## 📞 Support

**Files Included in Package**:
- `BACKUP_COMPLETE_SUMMARY.md` - Start here for overview
- `BACKUP_RECOVERY_GUIDE.md` - Comprehensive recovery guide
- `RESTORE_RECIPES.md` - This file (recipe collection)
- `BUNDLE_INVENTORY.txt` - Detailed inventory
- `PERF_BACKUP_QUICK_SHARE.txt` - Share-ready summary
- `PACKAGE_MANIFEST.txt` - Portable documentation

**Author**: arnab19111987-ops  
**Email**: arnab19111987@gmail.com  
**Repository**: https://github.com/arnab19111987-ops/Firstry

---

## ✅ Quick Reference Card

| Scenario | Recipe | File Needed | Size |
|----------|--------|-------------|------|
| Team has repo access | Recipe 1 (Incremental) | firsttry-perf-40pc.bundle | 106 KB |
| No repo access | Recipe 2 (Standalone) | firsttry-standalone.bundle | 80 MB |
| Code review | Recipe 3 (Patches) | patches-perf-40pc/*.patch | 2.2 MB |
| Already cloned | Recipe 4 (Fetch bundle) | Either bundle | - |
| Need hosted backup | Recipe 5 (Backup remote) | Git repo | - |

**Restoration Time**:
- Incremental: ~5 seconds
- Standalone: ~30 seconds  
- Patches: ~10 seconds
- Backup remote: ~2 minutes (includes repo creation)

---

**Last Updated**: November 11, 2025  
**Bundle Version**: v1.0  
**Status**: ✅ All bundles verified and tested
