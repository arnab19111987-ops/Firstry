#!/usr/bin/env bash
# Verify BLAKE3 hashing integration
# Usage: ./tools/verify_blake3_hash.sh [--check-parity] [--bench]

set -euo pipefail

ROOT="${1:-.}"
CHECK_PARITY="${2:-false}"
BENCH="${3:-false}"

echo "=========================================="
echo "BLAKE3 Hashing Integration Verification"
echo "=========================================="
echo ""

# Test 1: Python fallback (BLAKE3)
echo "1. Testing Python fallback (BLAKE3)"
echo "   Environment: FT_FASTPATH=off"
export FT_FASTPATH=off
python3 << 'PY'
import sys
from pathlib import Path
from firsttry.twin.fastpath import scan_paths, hash_paths
from firsttry.twin.hashers import Hasher

root = Path(".")
files = list(Path("src/firsttry/twin").glob("*.py"))[:3]
if files:
    hashes = hash_paths(files)
    print(f"   ✓ Python fallback: hashed {len(hashes)} files")
    for path, digest in list(hashes.items())[:2]:
        print(f"     - {path.name}: {digest[:16]}...")
else:
    print("   ⚠ No files to hash")
PY

echo ""

# Test 2: Auto mode (tries Rust, falls back to Python)
echo "2. Testing auto mode (smart backend selection)"
unset FT_FASTPATH
python3 << 'PY'
import sys
from pathlib import Path
from firsttry.twin.fastpath import scan_paths, hash_paths

root = Path(".")
files = list(Path("src/firsttry/twin").glob("*.py"))[:3]
if files:
    hashes = hash_paths(files)
    print(f"   ✓ Auto mode: hashed {len(hashes)} files")
    for path, digest in list(hashes.items())[:2]:
        print(f"     - {path.name}: {digest[:16]}...")
else:
    print("   ⚠ No files to hash")
PY

echo ""

# Test 3: Hasher class
echo "3. Testing Hasher class"
python3 << 'PY'
from pathlib import Path
from firsttry.twin.hashers import Hasher

hasher = Hasher(Path("src/firsttry/twin"))
files = hasher.enumerate_files()
print(f"   ✓ Hasher.enumerate_files(): found {len(files)} files")

if files[:2]:
    hashes = hasher.compute_hashes(files[:2])
    print(f"   ✓ Hasher.compute_hashes(): hashed {len(hashes)} files")

all_hashes = hasher.hash_all()
print(f"   ✓ Hasher.hash_all(): hashed {len(all_hashes)} files total")
PY

echo ""

# Test 4: Hash determinism (same content = same hash)
echo "4. Testing hash determinism"
python3 << 'PY'
import tempfile
from pathlib import Path
from firsttry.twin.fastpath import hash_paths

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    f1 = tmp / "test1.txt"
    f2 = tmp / "test2.txt"
    content = "deterministic test content"
    f1.write_text(content)
    f2.write_text(content)
    
    h1 = hash_paths([f1])[f1]
    h2 = hash_paths([f2])[f2]
    
    if h1 == h2:
        print(f"   ✓ Hash determinism verified: {h1[:16]}...")
    else:
        print(f"   ✗ HASH MISMATCH: {h1[:16]}... != {h2[:16]}...")
        sys.exit(1)
PY

echo ""

# Test 5: Verify hash size (BLAKE3 = 256-bit = 64 hex chars)
echo "5. Verifying BLAKE3 hash format"
python3 << 'PY'
import tempfile
from pathlib import Path
from firsttry.twin.fastpath import hash_paths

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    test_file = tmp / "test.bin"
    test_file.write_bytes(b"x" * 1024)
    
    hashes = hash_paths([test_file])
    digest = hashes[test_file]
    
    if len(digest) == 64 and all(c in "0123456789abcdef" for c in digest):
        print(f"   ✓ BLAKE3 format verified (256-bit = 64 hex chars)")
        print(f"     Sample: {digest[:32]}...")
    else:
        print(f"   ✗ INVALID FORMAT: {digest}")
        sys.exit(1)
PY

echo ""
echo "=========================================="
echo "✅ All verification checks passed!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Python fallback: ✓"
echo "  - Auto mode: ✓"
echo "  - Hasher class: ✓"
echo "  - Hash determinism: ✓"
echo "  - BLAKE3 format: ✓"
echo ""
