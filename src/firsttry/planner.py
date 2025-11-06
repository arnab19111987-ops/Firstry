# firsttry/planner.py
from pathlib import Path

from .detectors import detect_languages
from .pipelines import LANGUAGE_PIPELINES


def build_plan(root: str = ".") -> dict:
    root_path = Path(root).resolve()
    langs = detect_languages(root_path)

    steps = []
    for lang in langs:
        pipeline = LANGUAGE_PIPELINES.get(lang, [])
        for step in pipeline:
            steps.append(
                {
                    "lang": lang,
                    "id": step["id"],
                    "run": step["run"],
                    "autofix": step.get("autofix", []),
                    "optional": step.get("optional", False),
                    "tier": step.get("tier", 1),
                },
            )

    return {
        "root": str(root_path),
        "languages": list(langs),
        "steps": steps,
    }
