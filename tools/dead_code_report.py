#!/usr/bin/env python3
"""Combine all dead code signals into one report."""
import json

print("# " + "=" * 78)
print("# DEAD CODE ANALYSIS REPORT")
print("# " + "=" * 78)

# Load coverage data
with open('coverage.json') as f:
    cov_data = json.load(f)

files_data = cov_data.get('files', {})
zero_cov_files = set()

for path, info in files_data.items():
    if not path.startswith('src/firsttry'):
        continue
    if path.startswith('src/firsttry/tests/'):
        continue
    summary = info.get('summary', {})
    if summary.get('percent_covered', 0) == 0:
        zero_cov_files.add(path)

# Read orphan list from previous run
orphans_from_import_graph = {
    "src/firsttry/changed.py",
    "src/firsttry/changes.py",
    "src/firsttry/ci_mapper_impl.py",
    "src/firsttry/cli_ci_parity.py",
    "src/firsttry/cli_dag.py",
    "src/firsttry/cli_enhanced.py",
    "src/firsttry/cli_pipelines.py",
    "src/firsttry/cli_run_profile.py",
    "src/firsttry/cli_runner_light.py",
    "src/firsttry/cli_stable.py",
    "src/firsttry/cli_v2.py",
    "src/firsttry/config.py",
    "src/firsttry/db_pg.py",
    "src/firsttry/db_sqlite.py",
    "src/firsttry/device.py",
    "src/firsttry/docker_smoke.py",
    "src/firsttry/env.py",
    "src/firsttry/gate_guard.py",
    "src/firsttry/legacy_quarantine/gates_backup/__init__.py",
    "src/firsttry/legacy_quarantine/gates_backup/base.py",
    "src/firsttry/legacy_quarantine/gates_backup/ci_files_changed.py",
    "src/firsttry/legacy_quarantine/gates_backup/config_drift.py",
    "src/firsttry/legacy_quarantine/gates_backup/coverage_check.py",
    "src/firsttry/legacy_quarantine/gates_backup/deps_lock.py",
    "src/firsttry/legacy_quarantine/gates_backup/drift_check.py",
    "src/firsttry/legacy_quarantine/gates_backup/env_tools.py",
    "src/firsttry/legacy_quarantine/gates_backup/go_tests.py",
    "src/firsttry/legacy_quarantine/gates_backup/node_tests.py",
    "src/firsttry/legacy_quarantine/gates_backup/precommit_all.py",
    "src/firsttry/legacy_quarantine/gates_backup/python_lint.py",
    "src/firsttry/legacy_quarantine/gates_backup/python_mypy.py",
    "src/firsttry/legacy_quarantine/gates_backup/python_pytest.py",
    "src/firsttry/legacy_quarantine/gates_backup/security_bandit.py",
    "src/firsttry/legacy_quarantine/legacy_checks.py",
    "src/firsttry/license_cache.py",
    "src/firsttry/license_fast.py",
    "src/firsttry/mapper.py",
    "src/firsttry/models.py",
    "src/firsttry/performance_targets.py",
    "src/firsttry/performance_validator.py",
    "src/firsttry/pipelines.py",
    "src/firsttry/pro_features.py",
    "src/firsttry/profiles.py",
    "src/firsttry/progress.py",
    "src/firsttry/repo_state.py",
    "src/firsttry/report.py",
    "src/firsttry/run_swarm.py",
    "src/firsttry/runner/__init__.py",
    "src/firsttry/runner/config.py",
    "src/firsttry/runner/executor.py",
    "src/firsttry/runner/model.py",
    "src/firsttry/runner/planner.py",
    "src/firsttry/runner/state.py",
    "src/firsttry/runner/taskcache.py",
    "src/firsttry/runner_light.py",
    "src/firsttry/scanner.py",
    "src/firsttry/self_repair.py",
    "src/firsttry/suggestion_engine.py",
    "src/firsttry/summary.py",
    "src/firsttry/tests/indexer.py",
    "src/firsttry/tests/prune.py",
    "src/firsttry/vscode_skel.py",
}

# Broken imports from smoke test
broken_imports = {
    "src/firsttry/cli_pipelines.py",
    "src/firsttry/cli_run_profile.py",
    "src/firsttry/cli_runner_light.py",
    "src/firsttry/cli_v2.py",
    "src/firsttry/orchestrator.py",
}

# Calculate intersections
high_confidence = orphans_from_import_graph & zero_cov_files
high_confidence_broken = high_confidence & broken_imports

print("\n## TIER 1: HIGH CONFIDENCE DELETIONS")
print("## (Orphaned + 0% coverage + broken imports)")
print(f"## Count: {len(high_confidence_broken)}")
print("# " + "-" * 78)
for f in sorted(high_confidence_broken):
    print(f"  {f}")

print("\n## TIER 2: VERY SAFE DELETIONS")
print("## (Orphaned + 0% coverage, imports work but never used)")
print(f"## Count: {len(high_confidence - broken_imports)}")
print("# " + "-" * 78)
for f in sorted(high_confidence - broken_imports):
    print(f"  {f}")

print("\n## TIER 3: LIKELY DEAD (Orphaned but not in coverage data)")
print(f"## Count: {len(orphans_from_import_graph - zero_cov_files)}")
print("# " + "-" * 78)
for f in sorted(orphans_from_import_graph - zero_cov_files):
    print(f"  {f}")

print("\n## SPECIAL CASE: legacy_quarantine/ directory")
print("## This entire directory appears to be orphaned (0 external references)")
print("# " + "-" * 78)
legacy_files = [f for f in orphans_from_import_graph if 'legacy_quarantine' in f]
print(f"  Files in legacy_quarantine/: {len(legacy_files)}")
for f in sorted(legacy_files)[:5]:
    print(f"    {f}")
if len(legacy_files) > 5:
    print(f"    ... and {len(legacy_files) - 5} more")

print("\n## SUMMARY STATISTICS")
print("# " + "=" * 78)
print("  Total source files analyzed: ~181")
print(f"  Files with 0% coverage: {len(zero_cov_files)}")
print(f"  Orphaned files (unreachable): {len(orphans_from_import_graph)}")
print(f"  Broken imports (can't even load): {len(broken_imports)}")
print("  ")
print(f"  HIGH CONFIDENCE deletions: {len(high_confidence_broken)}")
print(f"  VERY SAFE deletions: {len(high_confidence - broken_imports)}")
print(f"  LIKELY DEAD: {len(orphans_from_import_graph - zero_cov_files)}")
print("  ")
print(f"  TOTAL SAFE TO DELETE: {len(high_confidence) + len(orphans_from_import_graph - zero_cov_files)}")

print("\n## RECOMMENDED ACTION PLAN")
print("# " + "=" * 78)
print("  1. Delete legacy_quarantine/ entirely (15 files, 0 external refs)")
print("  2. Delete TIER 1 files (broken imports, never used)")
print("  3. Delete TIER 2 files (working imports, never used)")
print("  4. Consider TIER 3 on case-by-case basis")
print("  5. Run tests after each deletion to confirm")

print("\n## SPECIFIC FILES TO DELETE (Quick Win)")
print("# " + "=" * 78)
quick_wins = [
    "src/firsttry/legacy_quarantine/",  # entire directory
    "src/firsttry/vscode_skel.py",      # 0 refs, 0% cov
    "src/firsttry/sync.py",              # self-ref only, 0% cov
    "src/firsttry/setup_wizard.py",      # self-ref only, 0% cov
    "src/firsttry/cli_pipelines.py",     # broken import
    "src/firsttry/cli_run_profile.py",   # broken import
    "src/firsttry/cli_runner_light.py",  # broken import
    "src/firsttry/cli_v2.py",            # broken import
]
for f in quick_wins:
    print(f"  {f}")
