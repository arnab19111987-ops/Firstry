#!/usr/bin/env bash
# Fast-path repository hashing verification script
# Usage: bash tools/verify_hash_speed.sh [root_path] [iterations]

ROOT="${1:-.}"
ITERATIONS="${2:-1}"

echo "=================================="
echo "Fast-Path Hash Verification"
echo "=================================="
echo "Root: $ROOT"
echo "Iterations: $ITERATIONS"
echo ""

python3 - "$ROOT" "$ITERATIONS" << 'PYEOF'
import sys
import time
import os
from pathlib import Path
from firsttry.twin.fastpath import scan_paths, hash_paths

root = Path(sys.argv[1])
iterations = int(sys.argv[2])

print("== Test 1: Python Fallback (BLAKE3) ==")
os.environ["FT_FASTPATH"] = "off"
for i in range(1, iterations + 1):
    print(f"Run {i}:")
    t0 = time.time()
    files = scan_paths(root)
    t_scan = time.time()
    hashes = hash_paths(files)
    t_hash = time.time()
    
    print(f"  files={len(files)} scan={t_scan-t0:.3f}s hash={t_hash-t_scan:.3f}s total={t_hash-t0:.3f}s")
    if hashes:
        sample = list(hashes.values())[:2]
        print(f"  sample_hashes={sample}")
    print()

print("== Test 2: Auto Mode (Rust if available) ==")
os.environ.pop("FT_FASTPATH", None)
for i in range(1, iterations + 1):
    print(f"Run {i}:")
    t0 = time.time()
    files = scan_paths(root)
    t_scan = time.time()
    hashes = hash_paths(files)
    t_hash = time.time()
    
    print(f"  files={len(files)} scan={t_scan-t0:.3f}s hash={t_hash-t_scan:.3f}s total={t_hash-t0:.3f}s")
    if hashes:
        sample = list(hashes.values())[:2]
        print(f"  sample_hashes={sample}")
    print()

print("== Test 3: Hash Parity Verification ==")
os.environ["FT_FASTPATH"] = "off"
files = scan_paths(root)
test_files = files[:20] if len(files) > 20 else files

if not test_files:
    print("  No files to test. Skipping parity check.")
else:
    hashes_py = hash_paths(test_files)
    print(f"  Python fallback: {len(hashes_py)} files hashed")
    
    os.environ.pop("FT_FASTPATH", None)
    hashes_auto = hash_paths(test_files)
    print(f"  Auto mode: {len(hashes_auto)} files hashed")
    
    matches = 0
    for f in test_files:
        if f in hashes_py and f in hashes_auto:
            if hashes_py[f] == hashes_auto[f]:
                matches += 1
    
    total = len(test_files)
    if matches == total:
        print(f"  ✓ Parity: {matches}/{total} files have identical digests")
    else:
        print(f"  ✗ Parity FAILED: {matches}/{total} files match")

print("\n== Verification Complete ==")
PYEOF
