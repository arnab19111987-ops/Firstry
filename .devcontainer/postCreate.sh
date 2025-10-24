#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install build twine ruff black mypy pytest coverage rich pyyaml jinja2 click
npm i -g actionlint || true
