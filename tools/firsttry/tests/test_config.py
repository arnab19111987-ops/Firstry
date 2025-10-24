from pathlib import Path
from firsttry.config import FirstTryConfig


def test_defaults(tmp_path: Path):
    cfg = FirstTryConfig.load(tmp_path)  # no file
    assert cfg.coverage_threshold == 80
    assert "not integration" in cfg.pytest_smoke_expr


def test_load_from_yaml(tmp_path: Path):
    (tmp_path / ".firsttry.yml").write_text(
        "coverage_threshold: 92\npytest_smoke_expr: 'not slow'\n", encoding="utf-8"
    )
    cfg = FirstTryConfig.load(tmp_path)
    assert cfg.coverage_threshold == 92
    assert cfg.pytest_smoke_expr == "not slow"
