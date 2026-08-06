#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
uv sync --frozen
uv run python scripts/generate_client_configs.py
printf '%s\n' "Generated: $root/dist/opencode.mcp.jsonc"
printf '%s\n' "Generated: $root/dist/aionui.mcp.json"
