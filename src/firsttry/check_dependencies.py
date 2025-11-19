from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from .check_registry import CHECK_REGISTRY


@dataclass
class DependencyRule:
    """Defines a conditional dependency between checks"""

    dependent: str  # Check that depends on another
    prerequisite: str  # Check that must succeed first
    reason: str  # Human-readable reason for dependency
    strict: bool = False  # If True, prerequisite failure blocks dependent completely


# Define logical dependencies between checks
DEPENDENCY_RULES: List[DependencyRule] = [
    # Syntax checks must pass before type checking
    DependencyRule(
        dependent="mypy",
        prerequisite="ruff",
        reason="Skip mypy type checking if ruff finds syntax errors",
        strict=True,
    ),
    # Tests should only run if basic linting passes
    DependencyRule(
        dependent="pytest",
        prerequisite="ruff",
        reason="Skip pytest if code has syntax/import errors",
        strict=False,  # Still run in strict mode
    ),
    # CI parity checks should run after basic validation
    DependencyRule(
        dependent="ci-parity",
        prerequisite="ruff",
        reason="Skip CI parity if basic code quality fails",
        strict=False,
    ),
    # NPM tests depend on no major Python issues (if it's a mixed project)
    DependencyRule(
        dependent="npm test",
        prerequisite="ruff",
        reason="Skip npm tests if Python code has syntax errors (mixed projects)",
        strict=False,
    ),
]


def get_dependency_graph() -> Dict[str, List[str]]:
    """Build a dependency graph from rules"""
    graph: Dict[str, List[str]] = {}
    for rule in DEPENDENCY_RULES:
        if rule.dependent not in graph:
            graph[rule.dependent] = []
        graph[rule.dependent].append(rule.prerequisite)
    return graph


def get_prerequisites(check_name: str) -> List[DependencyRule]:
    """Get all dependency rules for a specific check"""
    return [rule for rule in DEPENDENCY_RULES if rule.dependent == check_name]


def should_skip_due_to_dependencies(
    check_name: str, failed_checks: Set[str], profile: str = "dev"
) -> Optional[DependencyRule]:
    """
    Determine if a check should be skipped due to failed prerequisites.
    Returns the blocking rule if skip is needed, None otherwise.
    """

    prerequisites = get_prerequisites(check_name)

    for rule in prerequisites:
        prerequisite_failed = rule.prerequisite in failed_checks

        if prerequisite_failed:
            # In strict profile, honor all dependencies
            if profile == "strict":
                return rule
            # In other profiles, only honor strict dependencies
            elif rule.strict:
                return rule

    return None


def analyze_dependency_impact(
    checks: List[str], failed_checks: Set[str], profile: str = "dev"
) -> Dict[str, Any]:
    """
    Analyze how many checks would be skipped due to dependencies.
    Returns impact analysis for optimization insights.
    """

    skipped_checks = {}
    total_skipped = 0

    for check in checks:
        blocking_rule = should_skip_due_to_dependencies(check, failed_checks, profile)
        if blocking_rule:
            skipped_checks[check] = {
                "prerequisite": blocking_rule.prerequisite,
                "reason": blocking_rule.reason,
                "strict": blocking_rule.strict,
            }
            total_skipped += 1

    return {
        "total_checks": len(checks),
        "skipped_checks": total_skipped,
        "skipped_details": skipped_checks,
        "efficiency_gain": f"{total_skipped}/{len(checks)} checks skipped",
        "profile": profile,
    }


def get_execution_order(checks: List[str]) -> List[List[str]]:
    """
    Calculate optimal execution order based on dependencies.
    Returns list of check groups that can run in parallel.
    """

    # Build dependency graph
    graph = get_dependency_graph()

    # Separate checks into those with/without dependencies
    dependent_checks = set(graph.keys())
    independent_checks = [c for c in checks if c not in dependent_checks]

    # Create execution levels
    execution_levels = []

    # Level 0: Independent checks (can run first)
    if independent_checks:
        execution_levels.append(independent_checks)

    # Group dependent checks by their prerequisites
    prerequisite_groups: Dict[Tuple[str, ...], List[str]] = {}
    for check in checks:
        if check in dependent_checks:
            prerequisites = graph[check]
            key = tuple(sorted(prerequisites))  # Create grouping key

            if key not in prerequisite_groups:
                prerequisite_groups[key] = []
            prerequisite_groups[key].append(check)

    # Add prerequisite groups as separate levels
    for group in prerequisite_groups.values():
        execution_levels.append(group)

    return execution_levels


def validate_dependency_rules() -> List[str]:
    """
    Validate that all dependency rules reference valid checks.
    Returns list of validation errors.
    """

    errors = []
    valid_checks = set(CHECK_REGISTRY.keys())

    for rule in DEPENDENCY_RULES:
        if rule.dependent not in valid_checks:
            errors.append(f"Invalid dependent check: {rule.dependent}")

        if rule.prerequisite not in valid_checks:
            errors.append(f"Invalid prerequisite check: {rule.prerequisite}")

        # Check for self-dependencies
        if rule.dependent == rule.prerequisite:
            errors.append(f"Self-dependency detected: {rule.dependent}")

    # Check for circular dependencies (simple cycle detection)
    graph = get_dependency_graph()
    visited = set()
    rec_stack = set()

    def has_cycle(node):
        if node in rec_stack:
            return True
        if node in visited:
            return False

        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, []):
            if has_cycle(neighbor):
                return True

        rec_stack.remove(node)
        return False

    for check in graph:
        if check not in visited:
            if has_cycle(check):
                errors.append(f"Circular dependency detected involving: {check}")

    return errors


def get_dependency_insights(checks: List[str]) -> Dict[str, Any]:
    """Get comprehensive insights about dependency relationships"""

    graph = get_dependency_graph()
    execution_order = get_execution_order(checks)

    # Calculate dependency statistics
    total_dependencies = len(DEPENDENCY_RULES)
    strict_dependencies = len([r for r in DEPENDENCY_RULES if r.strict])

    # Find most critical prerequisites (most depended upon)
    prerequisite_counts: Dict[str, int] = {}
    for rule in DEPENDENCY_RULES:
        prereq = rule.prerequisite
        prerequisite_counts[prereq] = prerequisite_counts.get(prereq, 0) + 1

    most_critical = (
        max(prerequisite_counts.items(), key=lambda x: x[1])
        if prerequisite_counts
        else None
    )

    return {
        "total_rules": total_dependencies,
        "strict_rules": strict_dependencies,
        "flexible_rules": total_dependencies - strict_dependencies,
        "execution_levels": len(execution_order),
        "checks_per_level": [len(level) for level in execution_order],
        "most_critical_prerequisite": most_critical,
        "dependency_graph": graph,
        "validation_errors": validate_dependency_rules(),
    }
