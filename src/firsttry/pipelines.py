# firsttry/pipelines.py

PYTHON_PIPELINE = [
    # TIER 1: fast, high-signal
    {
        "id": "py-lint",
        "run": ["ruff check .", "black --check --exclude='(.venv/|.venv-build/|venv/|env/|build/|dist/|node_modules/)' ."],
        "autofix": [
            "ruff check --fix .",
            "black --exclude='(.venv/|.venv-build/|venv/|env/|build/|dist/|node_modules/)' .",
        ],
        "tier": 1,
    },
    {
        "id": "py-type",
        "run": ["mypy ."],
        "tier": 1,
    },
    # TIER 2: slower
    {
        "id": "py-test",
        "run": ["pytest -q"],
        "tier": 2,
        "optional": True,
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
