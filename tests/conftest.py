"""Pytest configuration and quality gate hooks."""
import pytest
from typing import Any


def pytest_collection_modifyitems(config: Any, items: list) -> None:
    """Enforce reason= parameter on all skip and xfail markers.
    
    This hook runs after collection and validates that every skip/xfail marker
    has a 'reason' parameter. This ensures we maintain discipline around test
    quarantines - every skipped/xfailed test must justify why.
    """
    issues = []
    
    for item in items:
        # Check for skip markers without reason
        skip_markers = item.iter_markers('skip')
        for marker in skip_markers:
            if 'reason' not in marker.kwargs or not marker.kwargs.get('reason'):
                issues.append(
                    f"{item.nodeid}: @pytest.mark.skip must include reason= parameter"
                )
        
        # Check for xfail markers without reason
        xfail_markers = item.iter_markers('xfail')
        for marker in xfail_markers:
            if 'reason' not in marker.kwargs or not marker.kwargs.get('reason'):
                issues.append(
                    f"{item.nodeid}: @pytest.mark.xfail must include reason= parameter"
                )
    
    if issues:
        raise ValueError(
            "❌ Missing reason= on skip/xfail markers (required for test discipline):\n  "
            + "\n  ".join(issues)
        )
