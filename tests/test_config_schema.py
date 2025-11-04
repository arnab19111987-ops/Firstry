import tomllib
import pytest
pytest.importorskip("pydantic")
from pydantic import BaseModel


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
