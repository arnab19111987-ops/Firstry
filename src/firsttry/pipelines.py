# firsttry/pipelines.py

PYTHON_PIPELINE = [
    # TIER 1: fast, high-signal
    {
        "id": "py-lint",
        "run": [
            "ruff check src tests",
            "black --check src tests",
        ],
        "autofix": [
            "ruff check --fix src tests",
            "black src tests",
        ],
        "tier": 1,
    },
    # Move heavy type checking out of the default fast tier. Mypy can be run
    # in a stricter or optional tier so developers aren't blocked by typing
    # debt during quick local runs.
    {
        "id": "py-type",
        "run": ["mypy src tests"],
        "tier": 2,
        "optional": True,
    },
    # TIER 2: slower
    {
        "id": "py-test",
        "run": ["PYTHONPATH=src python -m pytest -q tests"],
        "tier": 1,
        "optional": False,
    },
    {
        "id": "py-coverage",
        "run": ["pytest --cov"],
        "tier": 2,
        "optional": True,
    },
    {
        "id": "py-security",
        "run": ["bandit -r ."],
        "tier": 2,
        "optional": True,
    },
]

NODE_PIPELINE = [
    # TIER 1
    {
        "id": "js-lint",
        "run": ["npx eslint ."],
        "autofix": ["npx eslint . --fix"],
        "tier": 1,
    },
    {
        "id": "js-type",
        "run": ["npx tsc --noEmit"],
        "tier": 1,
        "optional": True,  # TS can be slow on big projects
    },
    # TIER 2
    {
        "id": "js-test",
        "run": ["npm test -- --watch=false"],
        "tier": 2,
        "optional": True,
    },
]

GO_PIPELINE = [
    {"id": "go-lint", "run": ["golangci-lint run"], "tier": 1, "optional": True},
    {"id": "go-test", "run": ["go test ./..."], "tier": 2},
]

RUST_PIPELINE = [
    {
        "id": "rs-lint",
        "run": ["cargo clippy --all-targets --all-features -- -D warnings"],
        "tier": 1,
    },
    {"id": "rs-test", "run": ["cargo test"], "tier": 2},
]

INFRA_PIPELINE = [
    {"id": "docker-lint", "run": ["hadolint Dockerfile"], "tier": 2, "optional": True},
    {"id": "tf-lint", "run": ["tflint"], "tier": 2, "optional": True},
]

LANGUAGE_PIPELINES = {
    "python": PYTHON_PIPELINE,
    "node": NODE_PIPELINE,
    "go": GO_PIPELINE,
    "rust": RUST_PIPELINE,
    "infra": INFRA_PIPELINE,
}
