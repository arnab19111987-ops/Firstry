from pathlib import Path

import pytest

from firsttry import pipelines
from firsttry.plan_adapter import adapt_planner_steps
from firsttry import change_detector


def test_warm_mode_filters_out_node_checks(monkeypatch):
    # Build a combined plan (python + node)
    raw_steps = list(pipelines.PYTHON_PIPELINE) + list(pipelines.NODE_PIPELINE)
    plan = adapt_planner_steps(raw_steps)

    # Simulate git changed files containing only python files
    monkeypatch.setattr(change_detector, "get_changed_files", lambda repo_root='.' : ["src/app.py"])

    filtered = change_detector.filter_plan_by_changes(plan, repo_root='.', changed_only=True)

    # Ensure no node checks remain in the filtered plan (empty filtered list is acceptable)
    families = { (i.get('family') or '').lower() for i in filtered }
    assert 'node' not in families, f"Node-family checks should be skipped when only Python files changed: {families}"
    # If any checks remain, at least one should be a python-family check
    if filtered:
        assert 'python' in families or any('py-' in (i.get('id') or '') for i in filtered)
