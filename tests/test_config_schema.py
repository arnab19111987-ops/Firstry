import tomllib

try:
    from pydantic import BaseModel
except Exception:
    import pytest

    pytest.skip("pydantic not available", allow_module_level=True)


class Runner(BaseModel):
    max_workers: int
    default_timeout: int


class Tiers(BaseModel):
    order: list[str]


class Prioritization(BaseModel):
    severity_weights: dict
    blocking_bonus: int
    location_bonus: int
    default_base_priority: int


class Root(BaseModel):
    tiers: Tiers
    runner: Runner
    prioritization: Prioritization


def test_pyproject_schema_valid():
    data = tomllib.loads(open("pyproject.toml", "rb").read()).get("tool", {}).get("firsttry", {})
    Root(**data)  # raises if invalid
