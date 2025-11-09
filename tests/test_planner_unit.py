import importlib.machinery
import importlib.util
from pathlib import Path


def _load_planner_module():
    # planner package exists; load the planner.py module explicitly by path
    # parents[1] is the repository root (/workspaces/Firstry)
    src_path = Path(__file__).resolve().parents[1] / "src" / "firsttry" / "planner.py"
    loader = importlib.machinery.SourceFileLoader("firsttry_planner_module", str(src_path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    # Set package so relative imports in planner.py (e.g. from .detectors) work
    module.__package__ = "firsttry"
    loader.exec_module(module)
    return module


def test_build_plan_with_languages(monkeypatch, tmp_path):
    # Arrange: make a fake root and monkeypatch detect_languages and pipelines
    root = tmp_path / "proj"
    root.mkdir()

    planner = _load_planner_module()

    monkeypatch.setattr(planner, "detect_languages", lambda p: ["py"])
    planner.LANGUAGE_PIPELINES["py"] = [
        {"id": "fmt", "run": "black .", "autofix": ["black ."], "optional": False, "tier": 1}
    ]

    # Act
    result = planner.build_plan(str(root))

    # Assert
    assert isinstance(result, dict)
    assert result["root"] == str(Path(root).resolve())
    assert "py" in result["languages"]
    assert any(step["id"] == "fmt" for step in result["steps"])


def test_build_plan_no_languages(monkeypatch, tmp_path):
    # When detect_languages returns empty set, steps should be empty
    planner = _load_planner_module()
    monkeypatch.setattr(planner, "detect_languages", lambda p: [])
    planner.LANGUAGE_PIPELINES["py"] = []

    res = planner.build_plan(str(tmp_path))
    assert res["languages"] == []
    assert res["steps"] == []
