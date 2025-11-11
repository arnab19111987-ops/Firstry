#!/usr/bin/env python3
"""Smoke test all module imports to find broken/unused modules."""
import pkgutil
import importlib
import sys
import os

PKG = "firsttry"

# Ensure src is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

failed = []
succeeded = []

print(f"# Testing all imports in package '{PKG}'...")
print("# " + "=" * 70)

for m in pkgutil.walk_packages([f"src/{PKG}"], prefix=f"{PKG}."):
    name = m.name
    try:
        importlib.import_module(name)
        succeeded.append(name)
        print(f"✓ {name}")
    except Exception as e:
        failed.append((name, repr(e)))
        print(f"✗ {name}: {e}")

print("\n# " + "=" * 70)
print(f"# Summary:")
print(f"#   Succeeded: {len(succeeded)}")
print(f"#   Failed: {len(failed)}")

if failed:
    print("\n# Failed imports:")
    for name, err in failed:
        print(f"#   IMPORT_FAIL {name}")
        print(f"#     → {err}")

sys.exit(0 if not failed else 1)
