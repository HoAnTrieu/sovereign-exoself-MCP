#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${1:-}" != "--mock" ]]; then
  printf '%s\n' 'only --mock is supported by this smoke script' >&2
  exit 2
fi
SOVEREIGN_PROVIDER_MODE=mock uv run pytest tests/integration -q
