#!/usr/bin/env python3
"""Find orphaned Python modules not reachable from entry points."""
import ast
import os
import sys
import pathlib

PKG = "firsttry"  # package root
SRC = pathlib.Path("src") / PKG

# Choose reasonable roots (entry points + main modules)
ROOTS = {
    SRC / "__init__.py",
    SRC / "__main__.py",
    SRC / "cli.py",
    SRC / "cli_aliases.py",
    SRC / "checks_orchestrator.py",
    SRC / "checks_orchestrator_optimized.py",
    SRC / "cached_orchestrator.py",
    SRC / "lazy_orchestrator.py",
    SRC / "orchestrator.py",
}

# Build module->file map and import edges
mod_to_file = {}
edges = {}

for py in SRC.rglob("*.py"):
    # Skip __pycache__ and hidden directories
    if "__pycache__" in py.parts or any(p.startswith('.') for p in py.parts):
        continue
    
    mod = str(py.relative_to(SRC)).replace(os.sep, ".")[:-3]  # strip .py
    if mod.endswith(".__init__"):
        mod = mod[: -len(".__init__")]
    
    mod_to_file[mod] = py
    edges[mod] = set()
    
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"# Warning: could not parse {py}: {e}", file=sys.stderr)
        continue
    
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                # Extract base module name
                base = a.name.split(".")[0]
                edges[mod].add(base)
        elif isinstance(n, ast.ImportFrom):
            if n.module:
                # Handle relative imports
                if n.level > 0:
                    # Relative import - reconstruct full module name
                    parts = mod.split(".")
                    if n.level <= len(parts):
                        base_parts = parts[:-n.level] if n.level < len(parts) else []
                        if n.module:
                            full_mod = ".".join(base_parts + [n.module])
                        else:
                            full_mod = ".".join(base_parts)
                        edges[mod].add(full_mod.split(".")[0] if full_mod else "")
                else:
                    # Absolute import
                    base = n.module.split(".")[0]
                    edges[mod].add(base)

# Crawl from roots
seen = set()
stack = []

for r in ROOTS:
    if not r.exists():
        continue
    # map file path -> module
    mod = str(r.relative_to(SRC)).replace(os.sep, ".")[:-3]
    if mod.endswith(".__init__"):
        mod = mod[: -len(".__init__")]
    stack.append(mod)

while stack:
    m = stack.pop()
    if m in seen:
        continue
    seen.add(m)
    for dep in edges.get(m, ()):
        # Only follow internal package imports
        if dep in edges and dep not in seen:
            stack.append(dep)
        # Also check submodules
        for candidate_mod in edges.keys():
            if candidate_mod.startswith(dep + ".") and candidate_mod not in seen:
                stack.append(candidate_mod)

# Report orphan files under package (excluding tests)
orphans = []
for mod, fp in mod_to_file.items():
    if mod not in seen:
        orphans.append((str(fp), mod))

print("\n# Orphan candidate files (not reachable from roots):")
print("# ================================================")
for fp, mod in sorted(orphans):
    print(f"{fp:60} ({mod})")

print(f"\n# Summary:")
print(f"# Total modules analyzed: {len(mod_to_file)}")
print(f"# Reachable from roots: {len(seen)}")
print(f"# Orphan candidates: {len(orphans)}")

if orphans:
    print("\n# Roots used:")
    for r in sorted(ROOTS):
        exists = "✓" if r.exists() else "✗"
        print(f"#   {exists} {r}")
