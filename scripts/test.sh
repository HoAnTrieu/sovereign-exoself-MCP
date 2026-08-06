#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
uv run python -m sovereign_exoself_mcp --check
uv run python scripts/generate_client_configs.py
bash scripts/smoke_test.sh --mock
