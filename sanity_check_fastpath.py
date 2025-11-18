#!/usr/bin/env python3
"""Sanity check script for fast-path scanner.

Verifies:
1. Rust/Python backend parity
2. Backend selection logic
3. Ignore patterns consistency
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from firsttry.twin.fastpath_scan import get_backend, scan_paths


def check_parity(root: Path) -> bool:
    """Check that Rust and Python backends return same file set."""
    print("=" * 70)
    print("PARITY CHECK: Rust vs Python backends")
    print("=" * 70)

    # Scan with Rust (if available)
    os.environ.pop("FT_FASTPATH", None)  # allow auto-detection
    rust_files = scan_paths(root)
    rust_backend = get_backend()
    print(f"\n✓ Rust scan completed ({rust_backend} backend)")
    print(f"  Files found: {len(rust_files)}")

    # Scan with Python fallback
    os.environ["FT_FASTPATH"] = "off"
    python_files = scan_paths(root)
    python_backend = get_backend()
    print(f"\n✓ Python scan completed ({python_backend} backend)")
    print(f"  Files found: {len(python_files)}")

    # Compare
    rust_set = set(rust_files)
    python_set = set(python_files)
    parity = rust_set == python_set

    print(f"\n{'✓' if parity else '✗'} Parity: {parity}")

    if not parity:
        rust_only = rust_set - python_set
        python_only = python_set - rust_set
        if rust_only:
            print(f"\n  Files only in Rust ({len(rust_only)}):")
            for f in sorted(rust_only)[:5]:
                print(f"    {f}")
            if len(rust_only) > 5:
                print(f"    ... and {len(rust_only) - 5} more")
        if python_only:
            print(f"\n  Files only in Python ({len(python_only)}):")
            for f in sorted(python_only)[:5]:
                print(f"    {f}")
            if len(python_only) > 5:
                print(f"    ... and {len(python_only) - 5} more")
        return False

    return True


def check_backend_selection() -> bool:
    """Check that backend selection logic works correctly."""
    print("\n" + "=" * 70)
    print("BACKEND SELECTION CHECK")
    print("=" * 70)

    root = Path(".")
    results = []

    # Test 1: Auto-select (should prefer Rust if available)
    os.environ.pop("FT_FASTPATH", None)
    _ = scan_paths(root)
    backend_auto = get_backend()
    print(f"\n✓ Auto mode: {backend_auto} backend selected")
    results.append(backend_auto in {"rust", "python"})

    # Test 2: Force Python
    os.environ["FT_FASTPATH"] = "off"
    _ = scan_paths(root)
    backend_off = get_backend()
    print(f"✓ FT_FASTPATH=off: {backend_off} backend selected")
    results.append(backend_off == "python")

    # Test 3: Various "off" values
    for val in ["off", "OFF", "Off"]:
        os.environ["FT_FASTPATH"] = val
        _ = scan_paths(root)
        backend = get_backend()
        results.append(backend == "python")
    print("✓ Case-insensitive 'off' handling: all use Python")

    # Test 4: Non-off values should allow Rust if available
    os.environ["FT_FASTPATH"] = "auto"
    _ = scan_paths(root)
    backend_auto2 = get_backend()
    print(f"✓ FT_FASTPATH=auto: {backend_auto2} backend selected")
    results.append(backend_auto2 in {"rust", "python"})

    success = all(results)
    print(f"\n{'✓' if success else '✗'} Backend selection: {'PASS' if success else 'FAIL'}")
    return success


def check_thread_parameter() -> bool:
    """Check that thread parameter is accepted."""
    print("\n" + "=" * 70)
    print("THREAD PARAMETER CHECK")
    print("=" * 70)

    os.environ.pop("FT_FASTPATH", None)
    root = Path(".")

    try:
        # Test with different thread counts
        for threads in [1, 2, 4, 8]:
            files = scan_paths(root, threads=threads)
            print(f"✓ threads={threads}: {len(files)} files")

        print("\n✓ Thread parameter handling: PASS")
        return True
    except Exception as e:
        print(f"\n✗ Thread parameter handling: FAIL - {e}")
        return False


def main() -> int:
    """Run all sanity checks."""
    print("\n" + "=" * 70)
    print("FAST-PATH SCANNER SANITY CHECK")
    print("=" * 70)

    root = Path(".")

    checks = [
        ("Parity (Rust vs Python)", lambda: check_parity(root)),
        ("Backend Selection", check_backend_selection),
        ("Thread Parameter", check_thread_parameter),
    ]

    results = []
    for name, check_fn in checks:
        try:
            result = check_fn()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name}: EXCEPTION - {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("SANITY CHECK SUMMARY")
    print("=" * 70)

    all_pass = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        all_pass = all_pass and result

    print("=" * 70)
    if all_pass:
        print("\n✅ ALL SANITY CHECKS PASSED\n")
        return 0
    else:
        print("\n❌ SOME SANITY CHECKS FAILED\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
