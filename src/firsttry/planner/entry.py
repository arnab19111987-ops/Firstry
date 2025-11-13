from __future__ import annotations

from ..twin import ProjectTwin
from .dag import build_plan  # existing


def build_plan_from_twin(twin: ProjectTwin):
    """Stable entrypoint: planner consumes only the Twin, not ad-hoc detectors."""
    return build_plan(
        repo_root=twin.root,
        language=twin.language,
        detectors=twin.detectors,
        changed_files=twin.changed_files,
        ci_hints=twin.ci_hints,
    )
