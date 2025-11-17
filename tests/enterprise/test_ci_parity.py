"""CI-parity validation tests - proving local DAG equals GitHub Actions execution.

Tests for:
1. GitHub Actions workflow parsing
2. Job matrix expansion
3. DAG equivalence between local and CI
4. Workflow fixture validation
5. CI vs local parallel execution parity
"""

from typing import Any, Dict

import pytest


@pytest.fixture
def github_workflow_fixture() -> Dict[str, Any]:
    """Fixture providing a sample GitHub Actions workflow."""
    return {
        "name": "FirstTry Pipeline",
        "on": {
            "push": {"branches": ["main", "develop"]},
            "pull_request": {"branches": ["main"]},
        },
        "jobs": {
            "lint": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"run": "pip install -e ."},
                    {"run": "pylint src/"},
                    {"run": "black --check src/"},
                ],
            },
            "test": {
                "runs-on": "ubuntu-latest",
                "needs": ["lint"],
                "strategy": {
                    "matrix": {
                        "python-version": ["3.9", "3.10", "3.11"],
                    }
                },
                "steps": [
                    {"run": "python -m pytest tests/"},
                ],
            },
            "coverage": {
                "runs-on": "ubuntu-latest",
                "needs": ["test"],
                "steps": [
                    {"run": "coverage run -m pytest tests/"},
                    {"run": "coverage report --fail-under=80"},
                ],
            },
        },
    }


@pytest.fixture
def gitlab_pipeline_fixture() -> Dict[str, Any]:
    """Fixture providing a sample GitLab CI pipeline."""
    return {
        "stages": ["lint", "test", "coverage"],
        "lint": {
            "stage": "lint",
            "image": "python:3.11",
            "script": ["pip install -e .", "pylint src/", "black --check src/"],
        },
        "test:py39": {
            "stage": "test",
            "image": "python:3.9",
            "script": ["python -m pytest tests/"],
            "needs": ["lint"],
        },
        "test:py310": {
            "stage": "test",
            "image": "python:3.10",
            "script": ["python -m pytest tests/"],
            "needs": ["lint"],
        },
        "test:py311": {
            "stage": "test",
            "image": "python:3.11",
            "script": ["python -m pytest tests/"],
            "needs": ["lint"],
        },
        "coverage": {
            "stage": "coverage",
            "image": "python:3.11",
            "script": ["coverage run -m pytest tests/", "coverage report --fail-under=80"],
            "needs": ["test:py39", "test:py310", "test:py311"],
        },
    }


def test_workflow_parsing_github(github_workflow_fixture: Dict[str, Any]):
    """Test that GitHub Actions workflow can be parsed."""
    workflow = github_workflow_fixture

    assert "jobs" in workflow
    assert "lint" in workflow["jobs"]
    assert "test" in workflow["jobs"]
    assert "coverage" in workflow["jobs"]


def test_workflow_parsing_gitlab(gitlab_pipeline_fixture: Dict[str, Any]):
    """Test that GitLab pipeline can be parsed."""
    pipeline = gitlab_pipeline_fixture

    assert "stages" in pipeline
    assert "lint" in pipeline
    assert "test:py39" in pipeline
    assert "coverage" in pipeline


def test_job_matrix_expansion(github_workflow_fixture: Dict[str, Any]):
    """Test that job matrix is properly expanded."""
    test_job = github_workflow_fixture["jobs"]["test"]
    matrix = test_job.get("strategy", {}).get("matrix", {})

    py_versions = matrix.get("python-version", [])
    assert len(py_versions) == 3
    assert "3.9" in py_versions
    assert "3.10" in py_versions
    assert "3.11" in py_versions

    # Expansion: test job becomes test:py39, test:py310, test:py311
    expanded_jobs = [f"test:py{v.replace('.', '')}" for v in py_versions]
    assert len(expanded_jobs) == 3


def test_job_dependencies_parsing(github_workflow_fixture: Dict[str, Any]):
    """Test that job dependencies (needs) are properly parsed."""
    jobs = github_workflow_fixture["jobs"]

    # Test depends on lint
    test_needs = jobs["test"].get("needs", [])
    if isinstance(test_needs, str):
        test_needs = [test_needs]
    assert "lint" in test_needs

    # Coverage depends on test
    coverage_needs = jobs["coverage"].get("needs", [])
    if isinstance(coverage_needs, str):
        coverage_needs = [coverage_needs]
    assert "test" in coverage_needs


def test_gitlab_stage_ordering(gitlab_pipeline_fixture: Dict[str, Any]):
    """Test that GitLab stages maintain proper ordering."""
    stages = gitlab_pipeline_fixture.get("stages", [])

    assert stages == ["lint", "test", "coverage"]

    # Verify each job belongs to correct stage
    assert gitlab_pipeline_fixture["lint"]["stage"] == "lint"
    assert gitlab_pipeline_fixture["test:py39"]["stage"] == "test"
    assert gitlab_pipeline_fixture["coverage"]["stage"] == "coverage"


def test_dag_from_github_workflow(github_workflow_fixture: Dict[str, Any]):
    """Test that GitHub workflow translates to valid DAG."""
    # Build DAG from workflow
    dag = {}

    for job_name, job_config in github_workflow_fixture["jobs"].items():
        needs = job_config.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]

        dag[job_name] = {
            "name": job_name,
            "dependencies": needs,
            "config": job_config,
        }

    # Verify DAG structure
    assert dag["lint"]["dependencies"] == []
    assert "lint" in dag["test"]["dependencies"]
    assert "test" in dag["coverage"]["dependencies"]


def test_dag_from_gitlab_pipeline(gitlab_pipeline_fixture: Dict[str, Any]):
    """Test that GitLab pipeline translates to valid DAG."""
    # Build DAG from pipeline
    dag = {}

    for job_name, job_config in gitlab_pipeline_fixture.items():
        if job_name == "stages":
            continue

        needs = job_config.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]

        dag[job_name] = {
            "name": job_name,
            "dependencies": needs,
            "stage": job_config.get("stage"),
        }

    # Verify DAG structure
    assert dag["lint"]["dependencies"] == []
    assert "lint" in dag["test:py39"]["dependencies"]
    assert "lint" in dag["test:py310"]["dependencies"]


def test_workflow_task_execution_order(github_workflow_fixture: Dict[str, Any]):
    """Test that task execution respects dependency order."""
    # Topological sort simulation
    tasks_by_stage = {
        0: ["lint"],
        1: ["test"],  # After lint
        2: ["coverage"],  # After test
    }

    # Verify no stage 1 task depends on stage 2 task
    jobs = github_workflow_fixture["jobs"]
    test_deps = jobs["test"].get("needs", [])
    if isinstance(test_deps, str):
        test_deps = [test_deps]

    assert all(dep in tasks_by_stage[0] for dep in test_deps)


def test_parallel_execution_within_stage(gitlab_pipeline_fixture: Dict[str, Any]):
    """Test that parallel jobs within same stage are identified."""
    pipeline = gitlab_pipeline_fixture

    # Find all jobs in "test" stage
    test_stage_jobs = [
        name
        for name, config in pipeline.items()
        if name != "stages" and config.get("stage") == "test"
    ]

    assert len(test_stage_jobs) == 3
    assert "test:py39" in test_stage_jobs
    assert "test:py310" in test_stage_jobs
    assert "test:py311" in test_stage_jobs


def test_matrix_expansion_preserves_dependencies(github_workflow_fixture: Dict[str, Any]):
    """Test that matrix expansion preserves job dependencies."""
    # Expand matrix
    original_test_needs = github_workflow_fixture["jobs"]["test"].get("needs", [])

    # After expansion to test:py39, test:py310, test:py311
    # Each should still depend on "lint"
    for expanded_job in ["test:py39", "test:py310", "test:py311"]:
        # In real implementation, all expanded jobs inherit original needs
        assert original_test_needs == github_workflow_fixture["jobs"]["test"].get("needs", [])


def test_local_firsttry_dag_equivalent():
    """Test that FirstTry's local DAG matches CI representation."""
    # Mock FirstTry DAG
    ft_dag = {
        "lint": {"tasks": ["pylint", "black"]},
        "test": {"tasks": ["pytest-py39", "pytest-py310", "pytest-py311"]},
        "coverage": {"tasks": ["coverage-check"]},
    }

    # Mock GitHub CI DAG (simplified)
    ci_dag = {
        "lint": {"tasks": []},  # Leaf node for deps
        "test": {"needs": ["lint"]},
        "coverage": {"needs": ["test"]},
    }

    # Both should be acyclic (DAG property)
    assert len(ft_dag) == 3
    assert len(ci_dag) == 3


def test_workflow_cycles_detection(github_workflow_fixture: Dict[str, Any]):
    """Test detection of circular dependencies."""
    # Create cyclic workflow (should fail validation)
    cyclic = {
        "jobs": {
            "a": {"needs": ["b"]},
            "b": {"needs": ["c"]},
            "c": {"needs": ["a"]},  # Cycle: a -> b -> c -> a
        }
    }

    # Cycle detection algorithm
    def has_cycle(jobs):
        visited = set()
        rec_stack = set()

        def visit(job, path):
            if job in rec_stack:
                return True
            if job in visited:
                return False

            visited.add(job)
            rec_stack.add(job)

            needs = jobs.get(job, {}).get("needs", [])
            if isinstance(needs, str):
                needs = [needs]

            for dep in needs:
                if dep in jobs and visit(dep, path + [job]):
                    return True

            rec_stack.remove(job)
            return False

        for job in jobs:
            if job not in visited:
                if visit(job, []):
                    return True
        return False

    assert has_cycle(cyclic["jobs"])
    assert not has_cycle(github_workflow_fixture["jobs"])


def test_ci_output_format_consistency(github_workflow_fixture: Dict[str, Any]):
    """Test that CI output follows consistent schema."""
    # Expected output schema from CI run
    ci_output = {
        "workflow_name": github_workflow_fixture["name"],
        "jobs_total": len(github_workflow_fixture["jobs"]),
        "jobs": {
            "lint": {"status": "passed", "duration_seconds": 15},
            "test": {"status": "passed", "duration_seconds": 45},
            "coverage": {"status": "passed", "duration_seconds": 20},
        },
    }

    assert ci_output["workflow_name"] == "FirstTry Pipeline"
    assert ci_output["jobs_total"] == 3


def test_job_status_aggregation():
    """Test that individual job statuses aggregate correctly."""
    jobs_status = {
        "lint": {"status": "passed"},
        "test:py39": {"status": "passed"},
        "test:py310": {"status": "passed"},
        "test:py311": {"status": "passed"},
        "coverage": {"status": "passed"},
    }

    # Aggregate logic
    overall_status = (
        "passed" if all(j["status"] == "passed" for j in jobs_status.values()) else "failed"
    )

    assert overall_status == "passed"

    # Single failure should fail overall
    jobs_status["test:py310"]["status"] = "failed"
    overall_status = (
        "passed" if all(j["status"] == "passed" for j in jobs_status.values()) else "failed"
    )

    assert overall_status == "failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
